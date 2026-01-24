from extras import heaters
import math
import logging
import types

######################################################################
# Heater Class Overrides
######################################################################
def set_pwm(self, read_time, value):
    self.target_pwm = value
    value = 0
    
    # Check if schedule exists and if it is durring the scheduled time
    sched = getattr(self, "schedule", None)
    if sched and self.target_value != 0 and "start_time" in sched and "end_time" in sched and "value" in sched:
        if sched["start_time"] <= self.printer.get_reactor().monotonic() + self.pwm_delay <= sched["end_time"]:
            value = sched["value"]
            
            # Ensures that all other heaters in the box are off
            if self.last_pwm_value == 0:
                for heater in self.box["heaters"]:
                    if heater != self:
                        heater.apply_pwm(read_time, 0)
                        
                    read_time += self.switching_delay # Ensures that the relay or ssr turns fully off before starting the next heater
    
    logging.debug(f"Read Time: {read_time}, Target Heater PWM Value: {value} Heater Request: {sched}")
    
    self.apply_pwm(read_time, value)

def schedule_pwm(self, time, start_time, value, end_time):    
    logging.debug(f"Time: {time} Heater {self.name} scheduling {start_time} to {end_time} with a pwm of: {value}")
    self.schedule = {"start_time": start_time, "end_time": end_time, "value": value}

######################################################################
# Heater Groups
######################################################################
class SharedHeaterGroup:
    def __init__(self, name, printer, cycle_time=1.0, max_active=1, is_bed=False, switching_delay=0.02):
        self.switching_delay = switching_delay
        self.name = name
        self.printer = printer
        self.reactor = printer.get_reactor()
        self.heaters = []
        self.cycle_time = cycle_time
        self.max_active = max_active
        self.last_idx = 0
        self.last_switch_time = 0.0
        self.active_heaters = []
        self.printer.register_event_handler("klippy:ready", self._late_init)
                
        if is_bed:
            self.set_as_bed()

    def register(self, heater):
        self.heaters.append(heater)
        heater.target_pwm = 0
        heater.switching_delay = self.switching_delay
        heater.box = {"id": -1,"heaters": [],"usage": 99999}
        
    def _late_init(self):
        # patch heaters AFTER MCU is ready
        for heater in self.heaters:
            heater.apply_pwm = heater.set_pwm
            heater.set_pwm = types.MethodType(set_pwm, heater)
            heater.schedule_pwm = types.MethodType(schedule_pwm, heater)
            

        # start timer only now
        self.reactor.register_timer(
            self._schedule_heaters,
            waketime=self.reactor.monotonic() + self.cycle_time
        )

    
    def set_as_bed(self):
        gcode = self.printer.lookup_object('gcode')
        gcode.register_command("M140", self.cmd_M140)
        gcode.register_command("M190", self.cmd_M190)
        
    def cmd_M140(self, gcmd, wait=False):
        # Set Bed Temperature
        temp = gcmd.get_float('S', 0.)
        num_of_heaters = len(self.heaters)
        for i in range(num_of_heaters):
            pheaters = self.printer.lookup_object('heaters')
            pheaters.set_temperature(self.heaters[i], temp, (wait and num_of_heaters-1==i)) # Will only wait for the last heater to reach its desired temperature so that all heaters heat up roughly simultaneously.
        
    def cmd_M190(self, gcmd):
        # Set Bed Temperature and Wait
        self.cmd_M140(gcmd, wait=True)

    def set_max_active(self, max_active):
        self.max_active = max_active
        
    def set_cycle_time(self, cycle_time):
        self.cycle_time = cycle_time

    def _schedule_heaters(self, eventtime):
        time = self.reactor.monotonic()   
        logging.debug("Scheduling Heaters")
        boxes = []
        for i in range(self.max_active):
            boxes.append({
                "id": i,
                "heaters": [],
                "usage": 0
                })
        
        for heater in self.heaters:
            heater_usage = heater.target_pwm
            
            # Skip unused heaters
            if heater_usage == 0:
                continue
            
            lowest_usage_box = {"id": -1,"heaters": [],"usage": 99999}
            
            # finds emptiest box
            for box in boxes:
                if lowest_usage_box["usage"] > box["usage"]:
                    lowest_usage_box = box
                    
            lowest_usage_box["heaters"].append(heater)
            lowest_usage_box["usage"] += heater_usage
        
        for box in boxes:
            # Skip scheduling empty boxes
            if box["usage"] == 0:
                continue
            
            scale_factor = self.cycle_time/box["usage"]     
            current_time = time
            
            for heater in box["heaters"]:
                # Calculate new pwm values and times
                new_time = heater.target_pwm * scale_factor - self.switching_delay
                new_time = max(new_time, 0.001)
                new_pwm = min(heater.target_pwm * (self.cycle_time/new_time), 1)
                
                # Calculate the equivilent power output
                equivalent_pwm = (new_time * new_pwm) / self.cycle_time
                #heater.last_pwm_value = equivalent_pwm
                
                # Schedule Heater
                heater.box = box
                heater.schedule_pwm(time, current_time, new_pwm, current_time + self.switching_delay + new_time)
                current_time += self.switching_delay + new_time

        return time + self.cycle_time


def load_config_prefix(config):
    name = config.get_name()
    short_name = name.split()[-1]
    
    cycle_time = config.getfloat('cycle_time', 1.0)
    max_active = config.getint('max_active', 1)
    is_bed = config.getboolean("is_bed", False)
    heaters = config.getlist("heaters")
    switching_delay = config.getfloat('switch_delay', 0.02)
    pheaters = config.get_printer().load_object(config, 'heaters')
    heater_group = SharedHeaterGroup(short_name, config.get_printer(), cycle_time, max_active, is_bed, switching_delay)
    for heater in heaters:
        heater_group.register(pheaters.lookup_heater(heater))
    
    return heater_group
