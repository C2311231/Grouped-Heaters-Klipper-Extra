# Grouped Heaters: Klipper Extra

A Klipper firmware extra to manage **multiple heaters in a shared group**, limiting simultaneous heating and enabling coordinated control to keep large multisegment heat beds within power constraints. Additionally can be used with any generic heaters.

---

This has not been tested on a real machine, however preformed as expected in the [Virtual-Klipper-Printer](https://github.com/mainsail-crew/virtual-klipper-printer) simulator by the Mainsail-Crew.

---

## Features

- **Grouped heater management**: Combine multiple heaters into a single logical group.  
- **Max active control**: Limit the number of heaters active at once (`max_active`) to prevent power surges.  
- **Cycle time control**: Switch heaters periodically to balance heating and prevent overshoot.  
- **Bed support**: Automatically register M140/M190 commands for grouped beds.
- **Individual Segment Temperature Control**: Allows each of the grouped heaters to have an independent target temperature while staying within power constraints.
- **PID Control Compatable**: Maintains support for both PID and BangBang heater control schemes.

## Installation

1. Download the python files from this repository into your ~/klipper/klippy/extras folder:  
2. Update your printer configuration (`printer.cfg`) to load the extra (MUST come after the heaters are defined in the config):

   ```ini
   [shared_heater_group {group_name}]
   cycle_time: 1 #(optional) The total time in seconds between heater scheduling (lower times increase heater responsiveness but reduses maximum power output). Default: `1.0` could cause problems if greater than 5.  
   max_active: 1 #(optional) Maximum number of heaters allowed to heat simultaneously. Default: `1`.
   is_bed: False #(optional) If true, registers M140/M190 commands for the group. (Can not have a seprate heatbed in configuration) 
   heaters: # (Required) A list of the names of all heaters (heater_generic recommended) in the group seperated by commas
   ```

3. Restart Klipper:

   ```bash
   sudo service klipper restart
   ```

Example:  

```ini
[heater_generic Heater1]
#...

[heater_generic Heater2]
#...

[shared_heater_group bed_group]
cycle_time: 1
max_active: 1
is_bed: True
heaters: Heater1, Heater2
```

## Known Limitations

- Does not always distribute power proportionally between heaters.
- Has a 20ms downtime between heater switches to prevent issues with ssr switching speed, so the maximum output power per cycle is redused

## Upcomming changes

- Add status reporting to shared groups
- Clean up the scheduler and better test it for errors
- Clean up comments

## License

This project is distributed under the **GNU GPLv3 license**, consistent with Klipper firmware.
