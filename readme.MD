# Laravel Installer

Laravel Installer is a desktop application for Ubuntu 22.04 and 24.04 that automates local setup for multiple Laravel projects. It provides a GUI for cloning repositories, preparing `.env`, detecting PHP requirements, installing missing packages, publishing Apache VirtualHosts, updating `/etc/hosts`, and linking each project's `public` directory into `/var/www/html`.

## What changed

This repository is now structured as a Python package instead of a single-file prototype.

- `laravel_installer/ui.py`: `customtkinter` desktop UI
- `laravel_installer/installer.py`: project install workflow and PHP detection
- `laravel_installer/system.py`: command execution, environment inspection, privileged helper client
- `laravel_installer/privileged_helper.py`: fixed-operation helper invoked through `pkexec`
- `scripts/build_deb.sh`: builds an `amd64 .deb` package with its own venv
- `tests/`: unit tests for config persistence, PHP version parsing, and helper validation

## Features

- Queue multiple Laravel projects
- Optional custom hostname and target directory per project
- Persist project list and base directory in `~/.config/laravel-installer/config.json`
- Generate a preparation summary before running installation
- Automatically detect missing `git`, `composer`, `apache2`, `pkexec`, PHP, PHP-FPM, and Laravel PHP extensions
- Use `pkexec` for privileged operations instead of collecting sudo password inside the app
- Retry only failed projects after a run
- Installable from a Debian package with desktop menu integration

## Runtime requirements

- Ubuntu 22.04 LTS or 24.04 LTS
- Python 3.10+
- `python3-tk`
- Desktop session with Polkit available
- Network access for Git, Composer, and apt package installation
- Public Git repositories or already-configured SSH access for private repositories

## Development run

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
python3 app.py
```

The app will auto-install `customtkinter` and `packaging` if they are missing when started via `python3 app.py`, but an editable install is the cleaner development path.

## Build the Debian package

```bash
chmod +x scripts/build_deb.sh
./scripts/build_deb.sh
```

The script builds:

- a private venv under `/opt/laravel-installer/venv`
- `/usr/bin/laravel-installer`
- `/usr/lib/laravel-installer/laravel-installer-helper`
- desktop entry and icon assets
- an `amd64 .deb` file under `build/`

Install the generated package with:

```bash
sudo apt install ./build/laravel-installer_1.0.1_amd64.deb
```

## Privileged operation model

The GUI runs unprivileged. System mutations are delegated to `laravel_installer.privileged_helper` through `pkexec`.

Supported privileged operations:

- `install_packages`
- `write_vhost`
- `enable_site`
- `reload_apache`
- `ensure_hosts_entry`
- `link_public_dir`
- `set_permissions`

The helper accepts structured JSON payloads only. It does not execute arbitrary shell commands.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

## Notes

- Apache is the only supported web server target in this release.
- Config data is preserved across upgrades because it lives in the user's home directory.
- HTTPS token flows are not implemented; repository access assumes public URLs or preconfigured SSH keys.
