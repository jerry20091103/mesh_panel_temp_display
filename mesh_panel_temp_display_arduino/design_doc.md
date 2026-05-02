# Mesh Panel Temperature Display
## Overview
The Mesh Panel Temperature Display is a mini hardware display designed to show the current PC temperature through a mesh panel. It utilizes a small OLED screen to provide real-time temperature readings. The numbers are displayed with small dots through the mesh, creating a seven-segment like appearance.
The display is powered by a MCU with Arduino that reads the temperature data from the PC through a USB connection. A companion software on the PC retrieves the temperature data and sends it to the display.
## Features
- Real-time temperature display through a mesh panel, up to 3 digits (xx.x °C or xxx °C)
- Configurable display "dots" to create a seven-segment like appearance. Can configure size and position of the dots to match any mesh panel pattern.
- Simple USB serial communication between the PC and the display
- Able to choose CPU/GPU or more temperature sources to display. Can also do a combined max of several temperature sources. (This is only on the PC software side, the display just receives a number to show)
## Details
### Dot Display Pattern
- The digit display has these parameters, they can determine the size and position of the dots to match the mesh panel pattern: (unit in pixels)
    - `startX`: The X coordinate of the top-left corner dot of the first digit
    - `startY`: The Y coordinate of the top-left corner dot of the first digit
    - `dotSize`: The diameter of each dot
    - `xXSpacing`: The x-offset to the next dot in the x direction
    - `xYSpacing`: The y-offset to the next dot in the x direction
    - `yXSpacing`: The x-offset to the next dot in the y direction
    - `yYSpacing`: The y-offset to the next dot in the y direction
    - `digitCount`: Number of digit slots to display. Valid values are 2, 3, or 4.
    - `unitSuffix`: Optional unit suffix shown after the last digit. Valid values are `C`, `F`, or blank.

- The position of the dots are illustrated in the diagram:
![dot display pattern](./dot_diagram.png)
- The whole digit group and optional unit suffix is treated as one display unit. The `startX` and `startY` values define the top-left corner dot of the first digit, and the spacing parameters determine the position of all dots for the configured digit count.
- For `digitCount = 2`, the display shows two whole digits with no decimal point.
- For `digitCount = 3`, the display shows either `xx.x` or `xxx` depending on the value.
- For `digitCount = 4`, the display shows either `xxx.x` or `xxxx` depending on the value.


### Extra Parameters
- `refreshInterval`: The time interval (in milliseconds) for refreshing the display with new temperature data
- `invertDisplay`: A boolean flag to determine whether to invert the display colors (white on black or black on white)
- `digitCount`: Choose how many digit slots to display on the OLED. This is currently hard coded in the firmware but will be sent from the PC software later.
- `unitSuffix`: Optional `C` or `F` suffix shown next to the last digit. This is also intended to be sent from the PC software later.
- Note: all the above parameters are sent to the display from the PC software, the display just receives the parameters and the temperature number to show.
### Communication Protocol
- UART Serial
- Allows realtime update of the configuration parameters and the temperature data
- Should have a simple watchdog mechanism to detect communication loss and display an error state
- The parameters are not stored in the MCU, they need to be sent from the PC software every time the display is powered on.
- Details: TBD (will be determined when during software design)
### Hardware
- MCU: Arduino Micro (ATmega32u4)
- Display: 128x64 OLED (SH1106 via I2C)
- Power: USB powered from the PC
- One LED for debugging and status indication
- One rst button to reset the MCU
- Uses native USB of the ATmega32u4 for communication and power, no additional USB to serial converter needed
- Has magnets on the PCB to attach to the mesh panel