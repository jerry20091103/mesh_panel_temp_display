# Build Instructions for Agents

This project is a PlatformIO Arduino firmware project.

Use this command from the repository root to build it on Windows:

```powershell
& "$env:USERPROFILE\.platformio\penv\Scripts\platformio.exe" run
```

Notes:

- The shorter `pio run` command may fail if PlatformIO is not on `PATH`.
- The active environment is `env:micro` in `platformio.ini`.
- A successful build should use the Arduino Micro / ATmega32U4 target.
