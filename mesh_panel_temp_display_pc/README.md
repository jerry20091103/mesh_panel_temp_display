# Mesh Panel Temperature Display (PC Application)

A Windows tray utility that monitors your PC's hardware temperatures and transmits the data to a dedicated Arduino-based display via a serial connection.

## Features
- **Tray Integration:** Runs in the system tray with a simple settings window.
- **Real-time Updates:** Automatically refreshes temperature data (CPU, GPU, etc.) at a configurable interval.
- **Configurable Display:** Easily adjust your display settings (number of digits, dot size, spacing, and inversion) via the app.
- **Auto-Discovery:** Automatically detects the Arduino connected via USB.

## Prerequisites
Before running the application, you must set up the system monitor:

1. **Install Libre Hardware Monitor**:
   - Download and install [Libre Hardware Monitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor).
   - Open the application.
   - Go to **Options > Remote Web Server > Run**.
   - (Optional) Check "Run on Windows Startup" for a seamless experience.
2. **Requirement**: Ensure the internal web server is accessible at `http://localhost:8085/data.json`.

## Installation & Setup

1. **Clone/Download** this repository.
2. **Navigate** to the `mesh_panel_temp_display_pc` folder.
3. **Install Python Dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```
4. **Run the Application**:
   - **Standard mode:** `python main.py`
   - **Minimized to tray:** `python main.py --minimized`
5. **Configure the Application:**
  1. General Settings: 
      - Open the application's "General" tab.
      - Set update interval, serial port (optional), and other preferences.
      - Select temperature source (CPU, GPU, or combined max). Then click "Save".
  2. Display Tuning:
      - Open the application's "Display Tuning" tab.
      - Adjust the number of digits, dot size, spacing, and inversion settings.
      - A preview will be shown in real-time. Click "Send Config" to save and transmit the settings to the Arduino.

## Startup & Integration
- **Auto-Start:** You can enable the "Start with Windows" option directly in the "General" settings tab of the application UI.
- **Standalone Executable:** To package the application into a single executable file (which simplifies distribution):
  ```powershell
  pyinstaller --noconfirm --onefile --windowed --name MeshPanelTemp main.py
  ```
  After packaging, the application can be placed in your startup folder or configured to launch on login.

## Technical Notes
- **Serial Protocol:** Uses 9600 baud with an ACK handshake.
- **Ports:** Automatically detects Arduino Micro (VID/PID) or matches by serial name.
- **Configuration:** User settings are saved in `%APPDATA%/MeshPanelTempDisplay/settings.json`.
; keep its web server enabled while the PC app is running.
