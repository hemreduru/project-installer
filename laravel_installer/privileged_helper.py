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


def run_operations(payload: dict[str, object]) -> None:
    operations = payload.get("operations", [])
    if not isinstance(operations, list):
        raise ValueError("operations must be a list")
    for item in operations:
        if not isinstance(item, dict):
            raise ValueError("each operation must be an object")
        operation = str(item.get("operation", "")).strip()
        op_payload = item.get("payload", {})
        if operation not in OPERATIONS or operation == "run_operations":
            raise ValueError(f"unsupported batch operation: {operation}")
        if not isinstance(op_payload, dict):
            raise ValueError("payload must be an object")
        OPERATIONS[operation](op_payload)


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


def configure_apache_php(payload: dict[str, object]) -> None:
    php_version = str(payload.get("php_version", "")).strip()
    if not php_version:
        raise ValueError("php_version is required")

    modules = ["proxy_fcgi", "setenvif", "rewrite"]
    for module in modules:
        run(["a2enmod", module])

    php_fpm_conf = f"php{php_version}-fpm"
    conf_path = Path("/etc/apache2/conf-available") / f"{php_fpm_conf}.conf"
    if conf_path.exists():
        run(["a2enconf", php_fpm_conf])

    run(["systemctl", "enable", "--now", f"php{php_version}-fpm"])
    run(["systemctl", "enable", "--now", "apache2"])


def ensure_service_running(payload: dict[str, object]) -> None:
    service_name = str(payload.get("service_name", "")).strip()
    if not service_name or "/" in service_name:
        raise ValueError("invalid service name")
    run(["systemctl", "enable", "--now", service_name])


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


def ensure_directory_owner(payload: dict[str, object]) -> None:
    path = Path(str(payload.get("path", "")))
    username = str(payload.get("username", "")).strip()
    if not username:
        raise ValueError("username is required")
    path.mkdir(parents=True, exist_ok=True)
    run(["chown", "-R", f"{username}:{username}", str(path)])
    run(["chmod", "775", str(path)])


OPERATIONS = {
    "install_packages": install_packages,
    "write_vhost": write_vhost,
    "enable_site": enable_site,
    "reload_apache": reload_apache,
    "ensure_hosts_entry": ensure_hosts_entry,
    "link_public_dir": link_public_dir,
    "set_permissions": set_permissions,
    "ensure_directory_owner": ensure_directory_owner,
    "configure_apache_php": configure_apache_php,
    "ensure_service_running": ensure_service_running,
    "run_operations": run_operations,
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
