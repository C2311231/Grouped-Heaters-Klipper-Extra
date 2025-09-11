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
2. Update your printer configuration (`printer.cfg`) to load the extra (MUST come before and other sections from this extra can be used):

   ```ini
   [shared_heater_groups]
   # No configuration section needed for the manager itself
   ```

3. Configure each shared heater identically to a generic heater with the addition of a share_group:  

   ```ini
   [grouped_heater my_heater_1]
   share_group: bed_group

   [grouped_heater my_heater_2]
   share_group: bed_group
   ```

4. (Optionally) Create a shared_heater_group to configure group settings.

   ```ini
   [shared_heater_group bed_group]
   cycle_time: 1 #(optional) Seconds between heater switches in a group. Default: `1.0`.  
   max_active: 1 #(optional) Maximum number of heaters allowed to heat simultaneously. Default: `1`.
   is_bed: False #(optional) If true, registers M140/M190 commands for the group. (Can not have a seprate heatbed in configuration) 
   ```

5. Restart Klipper:

   ```bash
   sudo service klipper restart
   ```

Example:  

```ini
[shared_heater_groups]

[grouped_heater bed_left]
share_group: bed_group
#...

[grouped_heater bed_right]
share_group: bed_group
#...

[shared_heater_group bed_group]
cycle_time: 1
max_active: 1
is_bed: True 
```

## Known Limitations

- Extra will prioritize heaters furthest from target temperature. So if a new heater is activated while others are at temperature they may be disabled until the new heater approaches its target.
- Mainsail may not display target temperature or allow setting it easily; gcode commands function normally.
- No support for extruders. (Was deemed unnecessary)

## Development Notes

- Only `set_pwm()` is overridden in the `Grouped_Heater` class; all other Heater functionality is inherited.
- Supports multiple heater types and combinations of control schemes.

## License

This project is distributed under the **GNU GPLv3 license**, consistent with Klipper firmware.
