from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def read_payload() -> dict[str, object]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    return json.loads(raw)


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def install_packages(payload: dict[str, object]) -> None:
    packages = payload.get("packages", [])
    if not isinstance(packages, list) or not all(isinstance(item, str) for item in packages):
        raise ValueError("packages must be a list of strings")
    if not packages:
        return
    run(["apt-get", "update"])
    run(["apt-get", "install", "-y", *packages])


def write_vhost(payload: dict[str, object]) -> None:
    site_name = str(payload.get("site_name", "")).strip()
    content = str(payload.get("content", ""))
    if not site_name or "/" in site_name:
        raise ValueError("invalid site name")
    target = Path("/etc/apache2/sites-available") / f"{site_name}.conf"
    target.write_text(content, encoding="utf-8")


def enable_site(payload: dict[str, object]) -> None:
    site_name = str(payload.get("site_name", "")).strip()
    if not site_name or "/" in site_name:
        raise ValueError("invalid site name")
    run(["a2ensite", f"{site_name}.conf"])


def reload_apache(_: dict[str, object]) -> None:
    run(["systemctl", "reload", "apache2"])


def ensure_hosts_entry(payload: dict[str, object]) -> None:
    hostname = str(payload.get("hostname", "")).strip().lower()
    if not hostname or any(char.isspace() for char in hostname):
        raise ValueError("invalid hostname")
    hosts_path = Path("/etc/hosts")
    content = hosts_path.read_text(encoding="utf-8")
    expected = f"127.0.0.1 {hostname}"
    if expected not in content:
        with hosts_path.open("a", encoding="utf-8") as handle:
            handle.write(f"\n{expected}\n")


def link_public_dir(payload: dict[str, object]) -> None:
    source = Path(str(payload.get("source", ""))).resolve()
    destination = Path(str(payload.get("destination", "")))
    if not source.exists():
        raise ValueError("public source does not exist")
    if destination.is_symlink() or destination.exists():
        if destination.is_dir() and not destination.is_symlink():
            shutil.rmtree(destination)
        else:
            destination.unlink()
    os.symlink(source, destination)


def set_permissions(payload: dict[str, object]) -> None:
    path = Path(str(payload.get("path", "")))
    username = str(payload.get("username", "")).strip() or "www-data"
    if not path.exists():
        raise ValueError("path does not exist")
    run(["chmod", "-R", "775", str(path)])
    run(["chown", "-R", f"www-data:{username}", str(path)])


OPERATIONS = {
    "install_packages": install_packages,
    "write_vhost": write_vhost,
    "enable_site": enable_site,
    "reload_apache": reload_apache,
    "ensure_hosts_entry": ensure_hosts_entry,
    "link_public_dir": link_public_dir,
    "set_permissions": set_permissions,
}


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("operation required")
    operation = sys.argv[1]
    if operation not in OPERATIONS:
        raise SystemExit(f"unsupported operation: {operation}")
    payload = read_payload()
    try:
        OPERATIONS[operation](payload)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
