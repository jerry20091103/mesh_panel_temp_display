# Arduino Firmware

This repository contains the firmware for the Arduino Micro, responsible for handling the serial communication and rendering the temperature onto the OLED display.

## Getting Started

### Prerequisites
- **Arduino IDE** or **PlatformIO CLI**
- **PlatformIO Core** (Required if using the command line or specialized environments)

### Building and Flashing
The project uses **PlatformIO** for its build system. 

1. **Install PlatformIO**:
   - Use the PlatformIO Core extension in VS Code. (Recommended)
   - Or install the PlatformIO Core in your Python environment: `pip install -lt platformio`
2. **Build and Upload**:
    - In the VSCode GUI:
        - Open the `mesh_panel_temp_display_arduino` folder in VSCode.
        - Use the PlatformIO toolbar to build and upload the firmware to your Arduino Micro.
    - With terminal:
        - Open a terminal in the `mesh_panel_temp_display_arduino` directory.
        - Run `platformio run --target release` to build the firmware.
        - Run `platformio run --target upload` to flash the firmware to your Arduino Micro.

## Project Structure
- **`src/`**: Contains the main application logic.
  - `main.cpp`: The main entry point for the firmware.
  - `SerialProtocol.cpp`: Implementation of the communication protocol.
  - `DotDisplayRenderer.cpp`: Logic for rendering the dots on the OLED.
- **`include/`**: Header files defining the interfaces and configurations.
  - `SerialProtocol.h`: Definitions for the serial communication.
  - `DotDisplayRenderer.h`: Definitions for the display rendering logic.
  - `DotDisplayConfigs.h`: Configuration constants for the display.
- **`platformio.ini`**: Configuration for the build environment (libraries, ports, and board definitions).

## Design Documentation
For a detailed overview of the protocol and hardware requirements, see:
- `design_doc.md` (Included in the project root or subdirectory)
