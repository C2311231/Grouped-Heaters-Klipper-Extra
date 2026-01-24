# Grouped Heaters: Klipper Extra

A experimental Klipper firmware extra to manage **multiple heaters in a shared group**, limiting simultaneous heating and enabling coordinated control to keep large multi-segment heat beds within power constraints. Additionally can be used with any generic heaters.

---

This has now been tested on a real machine for a short duration.
It is expected to be more extensively tested on a actual machine with a four segment heatbed in the coming weeks.

---

## Features

- **Grouped heater management**: Combine multiple heaters into a single logical group.  
- **Max active control**: Limit the number of heaters active at once (`max_active`) to prevent power surges.  
- **Cycle time control**: Switch heaters periodically to balance heating and prevent overshoot.  
- **Bed support**: Automatically register M140/M190 commands for grouped beds.
- **Individual Segment Temperature Control**: Allows each of the grouped heaters to have an independent target temperature while staying within power constraints.
- **PID Control Compatible**: Maintains support for both PID and BangBang heater control schemes.

## Installation

1. Clone this repository into your klipper extras:

   ```ini
   git clone https://github.com/C2311231/Grouped-Heaters-Klipper-Extra.git ~/klipper/klippy/extras/shared_heater_group/
   ```

2. Update your printer configuration (`printer.cfg`) to load the extra (MUST come after the heaters are defined in the config):

   ```ini
   [shared_heater_group {group_name}]
   cycle_time: 1 #(optional) The total time in seconds between heater scheduling (lower times increase heater responsiveness but reduces maximum power output). Default: `1.0` could cause problems if greater than 5.  
   max_active: 1 #(optional) Maximum number of heaters allowed to heat simultaneously. Default: `1`.
   is_bed: False #(optional) If true, registers M140/M190 commands for the group. (Can not have a separate heatbed in configuration) 
   heaters: # (Required) A list of the names of all heaters (heater_generic recommended) in the group separated by commas
   ```

3. Update your moonraker configuration to allow for updating:

   ```ini
   [update_manager Shared_Heater_Groups]
   type: git_repo
   path: ~/klipper/klippy/extras/shared_heater_group
   origin: https://github.com/C2311231/Grouped-Heaters-Klipper-Extra.git
   primary_branch: main
   is_system_service: false
   ```

4. Restart Klipper:

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

## PID Tuning

1. Disable Extra (Optional)

   WARNING  
      This step will disable the max active heater enforcement!! You will need to manually ensure that you limit the number of heaters you have enabled at any time to be below the capabilities of your system.

   For best results it is recommended to disable this extra while tunning the heaters, however it is not necessarily required. This can be done by commenting out the shared_heater_group sections in your config and then restarting klipper.

   ```ini
   #[shared_heater_group bed_group]
   #cycle_time: 1
   #max_active: 1
   #is_bed: True
   #heaters: Heater1, Heater2
   ```

2. Tune Each of the Heaters

   For each of the heaters run the PID_CALIBRATE command at your expected operating temperature one at a time. It is recommended that all other heaters remain off while each heater calibrates to ensure you remain below your power budget.

   ```ini
   PID_CALIBRATE HEATER=<your_heater_config_name> TARGET=<expected_temperature>
   ```

3. Save PID values

   Save the new PID values to your config.

   ```ini
   SAVE_CONFIG
   ```

4. Re-enable Extra

   Uncomment the config section from Step 1 (If commented previously). Then save and restart klipper. This will reactivate the extra and the heaters can again be used as normal.

   ```ini
   [shared_heater_group bed_group]
   cycle_time: 1
   max_active: 1
   is_bed: True
   heaters: Heater1, Heater2
   ```

## Known Limitations

- Does not always distribute power proportionally between heaters.
- Has a 20ms downtime between heater switches to prevent issues with ssr switching speed, so the maximum output power per cycle is reduced.
- It is not recommended to use with mechanical relays due to the high amount of switching involved
- Switches active heaters on and off at least once per cycle even if not required
- Reduces temperature control accuracy

## Upcoming changes

- Add status reporting to shared groups
- Clean up the scheduler and better test it for errors
- Clean up comments

## License

This project is distributed under the **GNU GPLv3 license**, consistent with Klipper firmware.
