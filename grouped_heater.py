# Support for a grouped heater
    
def load_config_prefix(config):
    return config.get_printer().lookup_object("shared_heater_groups").setup_shared_heater(config)