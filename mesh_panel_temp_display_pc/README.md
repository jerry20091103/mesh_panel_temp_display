# Mesh Panel Temperature Display (PC App)

Windows tray companion that reads PC temperatures and sends commands to the Arduino display via serial UART.

## Current implementation status

- Tray app with settings window and background loop
- Serial ACK queue for `COMMAND:VALUE\n` protocol
- Config command sender for all firmware parameters
- TEMP live updates (single or max-selected mode)
- Sensor discovery:
  - psutil temperature sensors
  - NVIDIA GPU temps via `nvidia-smi`
- Per-user settings persistence in `%APPDATA%/MeshPanelTempDisplay/settings.json`
- Optional per-user startup registration in Windows Run key
- One-digit "8" preview for mesh tuning geometry

## Run in development

Before launching the PC app, install Libre Hardware Monitor and enable its web server:

1. Install and run Libre Hardware Monitor.
2. In Libre Hardware Monitor, enable the Remote Web Server option.
    - Go to Options > Remote Web Server > Run
    - Also check "Run on Windows Startup" if you want it to start automatically.
3. Make sure the web server is running at `http://localhost:8085/data.json`.

1. Install dependencies:

```powershell
pip install -r requirements.txt
```

2. Launch:

```powershell
python main.py
```

3. Launch minimized to tray:

```powershell
python main.py --minimized
```

## Packaging target

Use PyInstaller for a single-file executable:

```powershell
pyinstaller --noconfirm --onefile --windowed --name MeshPanelTemp main.py
```

After packaging, startup registration points to the executable with `--minimized`.

## Notes

- Arduino firmware serial protocol uses 9600 baud and ACK handshake.
- Auto-port detects common Arduino Micro VID/PID and fallback keyword matching.
- LibreHardwareMonitor is used as the temperature source provider; keep its web server enabled while the PC app is running.
