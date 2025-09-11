from . import shared_heater_group

# Global Heater Groups Manager

class PrinterSharedHeaterGroups:
    def __init__(self, printer):
        self.groups = {}
        self.printer = printer
        printer.add_object('shared_heater_groups', self)

    def get_group(self, name, config=None):
        cycle_time = None
        max_active = None
        is_bed = None
        if config:
                cycle_time = config.getfloat('cycle_time', 1.0)
                max_active = config.getint('max_active', 1)
                is_bed = config.getboolean("is_bed", False)
        if name not in self.groups:
            if cycle_time and max_active and is_bed:
                self.groups[name] = shared_heater_group.SharedHeaterGroup(name, self.printer, cycle_time, max_active, is_bed)
            else:
                self.groups[name] = shared_heater_group.SharedHeaterGroup(name, self.printer)
            
        elif cycle_time and max_active and is_bed:
            self.groups[name].set_cycle_time(cycle_time)
            self.groups[name].set_max_active(max_active)
            if is_bed:
                self.groups[name].set_as_bed()

        return self.groups[name]
    
    def setup_shared_heater(self, config, gcode_id=None):
        printer = config.get_printer()
        heaters = printer.load_object(config, 'heaters')
        heater_name = config.get_name().split()[-1]
        if heater_name in heaters.heaters:
            raise config.error("Heater %s already registered" % (heater_name,))
        # Setup sensor
        sensor = heaters.setup_sensor(config)
        # Create heater
        heaters.heaters[heater_name] = heater = shared_heater_group.Grouped_Heater(config, sensor)
        heaters.register_sensor(config, heater, gcode_id)
        heaters.available_heaters.append(config.get_name())
        self.get_group(config.get('share_group')).register(heater)
        return heater
    
    
def load_config(config):
    return PrinterSharedHeaterGroups(config.get_printer())