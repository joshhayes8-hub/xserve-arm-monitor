# Xserve ARM Monitor

A lightweight web and native KDE desktop dashboard for monitoring [Automatic Ripping Machine (ARM)](https://github.com/automatic-ripping-machine/automatic-ripping-machine) on Debian-based systems.

The dashboard shows ARM service state, current ripping/transcoding activity, recent jobs, CPU utilisation, and processor temperatures. The desktop client and web dashboard share the same local Flask API.

> **Scope:** This project is a read-only monitoring interface. It does not install, modify, or control ARM, its ripping workers, MakeMKV, HandBrake, udev rules, or job scheduler.

## Components

- `src/app.py` — Flask API and web server
- `src/templates/index.html` — browser dashboard
- `src/desktop/main.py` — PySide6 desktop application
- `packaging/` — Debian service, launcher, desktop entry, defaults and maintainer scripts

## Requirements

- Debian 13 (amd64) is the current packaging target
- Automatic Ripping Machine installed and configured separately
- ARM service account named `arm`
- Python 3 and Flask for the web backend
- PySide6 Qt Widgets, `kdialog`, and `xdg-utils` for KDE desktop launching
- `pkexec` for the launcher's privileged service start/stop actions
- Access for the dashboard service account to the ARM database and log directory

## Configuration

The Debian package uses `/etc/default/xserve-arm-control`:

```sh
ARM_DB_PATH=/home/arm/db/arm.db
ARM_LOG_DIR=/home/arm/logs
ARM_SERVICE_NAME=armui
ARM_CONTROL_HOST=0.0.0.0
ARM_CONTROL_PORT=5000
XARMC_API=http://127.0.0.1:5000
```

Adjust these values for the local ARM installation. The web backend reads the ARM database and logs; it does not write to them. Keep the dashboard port restricted to a trusted network.

## Launcher

The KDE launcher provides exactly five actions: open the web dashboard, open the desktop application, open both applications, stop the background service, and start the background service. Starting or stopping the service uses the system's PolicyKit authentication prompt. Stopping the service disconnects both interfaces from live data but does not stop Automatic Ripping Machine or any ripping jobs.

## Development

Run the backend from the `src` directory after installing Flask:

```sh
python3 app.py
```

Run the desktop client in a graphical KDE session after installing PySide6:

```sh
python3 desktop/main.py
```

The desktop client connects to `http://127.0.0.1:5000` by default. Set `XARMC_API` to change the API endpoint.

## Debian packaging

The current package is `xserve-arm-control` version 1.0.3 for Debian 13 amd64. The package build tree is intentionally not committed; packaging metadata and scripts are in `packaging/`. Recreate the package by assembling the files under the standard Debian package layout and building with `dpkg-deb --build --root-owner-group`.

## Security and privacy

Do not commit ARM databases, logs, media paths, machine-specific IP addresses, credentials, API tokens, virtual environments, or generated `.deb` files. The repository `.gitignore` excludes common local runtime files.

## License

MIT. See [LICENSE](LICENSE).
