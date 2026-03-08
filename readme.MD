# Laravel Installer

> Turn a fresh Ubuntu machine into a Laravel-ready local environment in a few clicks.

`Laravel Installer` is a desktop app for Ubuntu that automates the repetitive parts of local Laravel setup: cloning repositories, preparing `.env`, resolving PHP requirements, installing missing packages, wiring Apache VirtualHosts, updating `/etc/hosts`, and publishing each app under `/var/www/html`.

Built for teams that spin up multiple Laravel projects often and want a cleaner flow than copy-pasting shell commands all day.

## Highlights

- Desktop GUI built with `customtkinter`
- Queue multiple Laravel projects in one run
- Auto-detect required PHP version from `composer.json`
- Auto-install missing PHP extensions and system dependencies
- Generate Apache VirtualHosts and local `.test` domains
- Persist project list and app preferences locally
- Retry only failed projects after a run
- Ship as an installable `amd64 .deb` package
- Use `pkexec` for privileged actions instead of asking for sudo inside the app

## What It Solves

Setting up one Laravel project is manageable.

Setting up five projects with different PHP requirements, Apache configs, `/etc/hosts` entries, permissions, Composer dependencies, and public symlinks is the part that gets old fast.

This app turns that setup into a repeatable GUI workflow.

## Supported Platform

- Ubuntu `22.04 LTS`
- Ubuntu `24.04 LTS`
- `amd64`
- Apache-based local environments

## Download

Latest packaged release:

- [GitHub Release: `v1.0.1`](https://github.com/hemreduru/project-installer/releases/tag/v1.0.1)

Direct install after download:

```bash
sudo apt install ./laravel-installer_1.0.2_amd64.deb
```

If you are building from this repository instead:

```bash
sudo apt install ./build/laravel-installer_1.0.2_amd64.deb
```

## How It Works

For each queued project, Laravel Installer can:

1. Clone the repository or pull the latest changes
2. Create `.env` from `.env.example` when needed
3. Detect the PHP version required by `composer.json`
4. Install missing PHP packages and extensions
5. Run `composer install`
6. Link the project's `public` directory into `/var/www/html`
7. Create an Apache VirtualHost
8. Add a local host entry such as `project-name.test`
9. Apply file permissions for local web serving

## Installation

### Option 1: Install the packaged app

```bash
sudo apt install ./laravel-installer_1.0.1_amd64.deb
```

Then launch it from:

- your applications menu as `Laravel Installer`
- or the terminal:

```bash
laravel-installer
```

### Option 2: Run in development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
python3 app.py
```

## Build The Debian Package

```bash
chmod +x scripts/build_deb.sh
./scripts/build_deb.sh
```

The build produces:

- `/usr/bin/laravel-installer`
- `/usr/lib/laravel-installer/laravel-installer-helper`
- desktop entry and icon assets
- Polkit policy file
- a release-ready `.deb` artifact under `build/`

## Runtime Requirements

- `python3`
- `python3-tk`
- `policykit-1`
- network access for Git, Composer, and apt
- public repositories or preconfigured SSH access for private ones

## Security Model

The GUI itself runs unprivileged.

System-changing operations are delegated to a fixed-operation helper through `pkexec`.

Allowed privileged actions:

- `install_packages`
- `write_vhost`
- `enable_site`
- `reload_apache`
- `ensure_hosts_entry`
- `link_public_dir`
- `set_permissions`

The helper accepts structured JSON payloads only. It does not execute arbitrary shell input.

## Project Layout

```text
laravel_installer/
├── ui.py                 # Desktop interface
├── installer.py          # Laravel setup workflow
├── system.py             # Command execution and environment inspection
├── privileged_helper.py  # pkexec-backed privileged operations
├── config.py             # Local config persistence
├── templates/            # Apache config template
├── assets/               # Desktop entry and icon
└── polkit/               # Polkit policy
```

## Tests

```bash
python3 -m unittest discover -s tests -v
```

## Notes

- Apache is the only supported web server target in this release.
- Config is stored under `~/.config/laravel-installer/config.json`.
- Config survives package upgrades because it lives in the user's home directory.
- Token-based Git auth flows are not built in yet; private repo access assumes SSH is already configured.

## License

[MIT](LICENSE)
