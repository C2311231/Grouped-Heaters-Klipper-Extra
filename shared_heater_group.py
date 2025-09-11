import random
import threading
from . import heaters

# Group Manager and Heater Class Overides

class Grouped_Heater(heaters.Heater):
    def __init__(self, config, sensor) -> None:
        super().__init__(config, sensor)
        self.printer = config.get_printer()
        self.group = config.get('share_group')
        
    def set_pwm(self, read_time, value):
        heater_group_manager = self.printer.lookup_object("shared_heater_groups")
        super().set_pwm(read_time, heater_group_manager.get_group(self.group).request_pwm(self,read_time,value))
    


# ######################################################################
# # Heater Groups
# ######################################################################
class SharedHeaterGroup:
    def __init__(self, name, printer, cycle_time=1.0, max_active=1, is_bed=False):
        self.name = name
        self.printer = printer
        self.heaters = []
        self.cycle_time = cycle_time
        self.max_active = max_active
        self.last_idx = 0
        self.last_switch_time = 0.0
        self.lock = threading.Lock()
        self.active_heaters = []
        
        if is_bed:
            self.set_as_bed()

    def register(self, heater):
        self.heaters.append(heater)
        
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

    def get_num_active_heaters(self):
        count = 0
        for heater in self.heaters:
            if heater.last_pwm_value != 0:
                count += 1
                
        return count

    def request_pwm(self, heater, read_time, value):
        with self.lock:
            if read_time - self.last_switch_time > self.cycle_time:
                random.shuffle(self.heaters)
                heaters_sorted = sorted(self.heaters, key=lambda x: (x.target_temp - x.last_temp))
                self.active_heaters = []
                for i in range(self.max_active):
                    self.active_heaters.append(heaters_sorted[i])
                
                self.last_switch_time = read_time

            if heater in self.active_heaters and self.get_num_active_heaters() < self.max_active:
                # Pass through real PWM
                return value
            else:
                # Suppress power, but let PID integrator continue
                return 0.0


def load_config_prefix(config):
    name = config.get_name()
    short_name = short_name = name.split()[-1]
    return config.get_printer().lookup_object("shared_heater_groups").get_group(short_name, config)