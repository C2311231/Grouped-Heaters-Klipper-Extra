from extras import heaters
import math
import logging
import types

######################################################################
# Heater Class Overrides
######################################################################
def set_pwm(self, read_time, value):
    heater_active = False
    for (start_time, end_time, pwm_value) in self.schedule:
        if start_time <= read_time + self.pwm_delay < end_time:
            heater_active = True
            if ((read_time < self.next_pwm_time or not self.last_pwm_value)
                and abs(value - self.last_pwm_value) < 0.05):
                # No significant change in value - can suppress update
                break
            
            ## Calculate scaled PWM value to ensure that heaters average out to the requested pwm power over the remainder of the cycle
            time_to_next_cycle = self.cycle_end_time - (read_time + self.pwm_delay)
            time_to_heater_off = end_time - (read_time + self.pwm_delay)
            pwm_scale = time_to_next_cycle / time_to_heater_off
            
            self.mcu_pwm.set_pwm(read_time + self.pwm_delay, min(value*pwm_scale, 1.0)) ## Pwm_delay is added to keep consistency with the original set_pwm function unknown if it is beneficial here
            self.last_pwm_value = value
            break
    
    if self.target_temp <= 0. or read_time > self.verify_mainthread_time:
        value = 0.
        
    pwm_time = read_time + self.pwm_delay
    self.next_pwm_time = (pwm_time + heaters.MAX_HEAT_TIME - (3. * self.pwm_delay + 0.001))
    self.target_pwm = value
    if value <= 0:
        pwm_time = read_time + self.pwm_delay
        self.mcu_pwm.set_pwm(pwm_time + self.pwm_delay, 0)

def schedule_pwm(self, start_time, value, end_time=None):
    self.mcu_pwm.set_pwm(start_time, value)
    self.last_pwm_value = value
    if end_time is not None:
        self.schedule.append((start_time, end_time, value))
        self.mcu_pwm.set_pwm(end_time, 0)

######################################################################
# Heater Groups
######################################################################
class SharedHeaterGroup:
    def __init__(self, name, printer, cycle_time=1.0, max_active=1, is_bed=False):
        self.name = name
        self.printer = printer
        self.reactor = printer.get_reactor()
        self.heaters = []
        self.cycle_time = cycle_time
        self.max_active = max_active
        self.last_idx = 0
        self.last_switch_time = 0.0
        self.active_heaters = []
        
        self.reactor.register_timer(self._schedule_heaters, waketime=self.reactor.monotonic()+0.5)
        
        if is_bed:
            self.set_as_bed()

    def register(self, heater):
        self.heaters.append(heater)
        heater.set_pwm = types.MethodType(set_pwm, heater)
        heater.schedule_pwm = types.MethodType(schedule_pwm, heater)
        heater.printer = self.printer
        heater.group = self.name
        heater.schedule = []
        heater.target_pwm = 0
        heater.cycle_end_time = 0
        heater.cycle_time = self.cycle_time
        
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
        total_heater_target_usage = 0
        for heater in self.heaters:
            total_heater_target_usage += heater.target_pwm
        
        # This is the size that each conceptual box should be assuming all heaters are smaller than the box
        total_box_size = total_heater_target_usage / self.max_active
        
        unpacked_heaters = list(self.heaters)
        # self.max_active is the number of boxes
        full_boxes = []
        
        for heater in list(unpacked_heaters):
            if heater.target_pwm >= total_box_size:
                unpacked_heaters.remove(heater)
                full_boxes.append([heater])
                total_heater_target_usage -= heater.target_pwm
                if self.max_active - len(full_boxes) > 0:
                    total_box_size = total_heater_target_usage / (self.max_active - len(full_boxes))
            
        remaining_boxes = []
        noMod = list(unpacked_heaters)
        logging.info(f"Full boxes: {full_boxes}, remaining heaters: {unpacked_heaters}, total_box_size: {total_box_size}")
        for heater in noMod:
            
            if len(full_boxes) + len(remaining_boxes) < self.max_active:
                remaining_boxes.append([heater])
                unpacked_heaters.remove(heater)
                continue
            
            lowest_usage_box_index = 0
            lowest_box_usage = math.inf
            for i in range(len(remaining_boxes)):
                box_usage = 0
                for remaining_heater in remaining_boxes[i]:
                    box_usage += remaining_heater.target_pwm
                if box_usage < lowest_box_usage:
                    lowest_box_usage = box_usage
                    lowest_usage_box_index = i
            remaining_boxes[lowest_usage_box_index].append(heater)   # May eventually want to change this to try and balance boxes better
            unpacked_heaters.remove(heater)
            
        duration_scale = 0
        boxes = remaining_boxes + full_boxes
        for box in boxes:
            box_usage = 0
            for heater in box:
                box_usage += heater.target_pwm
            if box_usage <= 0:
                scale_pwm = 0
            else:
                duration_scale = (1/box_usage)
                denom = self.cycle_time - len(box) * 0.02
                if denom <= 0:
                    # fallback: avoid division by zero / negative cycle window
                    logging.warning("cycle_time too small for number of heaters in box; skipping cycle adjustment")
                    scale_pwm = box_usage
                else:
                    # (1/duration_scale) == box_usage, keep original intent but safer
                    scale_pwm = box_usage * (self.cycle_time / denom)
            
            current_time = eventtime
            
            for heater in box:
                heater.schedule = []
                heater.cycle_end_time = eventtime + self.cycle_time
                start_time = current_time
                
                current_time += heater.target_pwm*duration_scale*self.cycle_time
                
                if current_time != start_time:
                    heater.schedule_pwm(start_time, min(scale_pwm, 1), max(start_time+0.01, current_time - 0.02))
                else:
                    heater.schedule_pwm(start_time, 0)
                    
                total_energy = (current_time - start_time) * min(scale_pwm, 1)
                equivalent_pwm = total_energy / self.cycle_time
                heater.last_pwm_value = equivalent_pwm
                ##logging.info(f"Heater {heater.name}: target={heater.target_pwm:.3f}, equivalent PWM={equivalent_pwm:.3f}")
                
                
        return eventtime + self.cycle_time


def load_config_prefix(config):
    name = config.get_name()
    short_name = name.split()[-1]
    
    cycle_time = config.getfloat('cycle_time', 1.0)
    max_active = config.getint('max_active', 1)
    is_bed = config.getboolean("is_bed", False)
    heaters = config.getlist("heaters")
    pheaters = config.get_printer().load_object(config, 'heaters')
    heater_group = SharedHeaterGroup(short_name, config.get_printer(), cycle_time, max_active, is_bed)
    for heater in heaters:
        heater_group.register(pheaters.lookup_heater(heater))
    
    return heater_group
