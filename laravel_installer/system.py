from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Iterable

from packaging.version import Version

from .models import CommandResult
from .utils import summarize_output


class CommandRunner:
    def run(
        self,
        command: list[str],
        cwd: Path | None = None,
        check: bool = True,
    ) -> CommandResult:
        completed = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            text=True,
            capture_output=True,
            check=False,
        )
        result = CommandResult(
            command=command,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
        if check and completed.returncode != 0:
            raise RuntimeError(
                f"Command failed ({completed.returncode}): {' '.join(command)}\n{summarize_output(completed.stderr or completed.stdout)}"
            )
        return result


class EnvironmentInspector:
    def __init__(self, runner: CommandRunner | None = None) -> None:
        self.runner = runner or CommandRunner()

    def command_exists(self, command: str) -> bool:
        return shutil.which(command) is not None

    def installed_php_versions(self) -> list[str]:
        versions: list[str] = []
        php_dir = Path("/usr/bin")
        if not php_dir.exists():
            return versions
        for path in php_dir.glob("php[0-9].[0-9]"):
            versions.append(path.name.replace("php", ""))
        return sorted(set(versions), key=Version)

    def ubuntu_version(self) -> str:
        os_release = Path("/etc/os-release")
        if not os_release.exists():
            return ""
        data = {}
        for line in os_release.read_text(encoding="utf-8").splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            data[key] = value.strip().strip('"')
        return data.get("VERSION_ID", "")

    def preflight_snapshot(self) -> dict[str, object]:
        return {
            "git": self.command_exists("git"),
            "composer": self.command_exists("composer"),
            "apache2": self.command_exists("apache2"),
            "pkexec": self.command_exists("pkexec"),
            "php_versions": self.installed_php_versions(),
            "ubuntu_version": self.ubuntu_version(),
        }


class PrivilegedOperations:
    def __init__(self, helper_command: list[str] | None = None) -> None:
        self.helper_command = helper_command or self._default_helper_command()

    def _default_helper_command(self) -> list[str]:
        packaged_helper = Path("/usr/lib/laravel-installer/laravel-installer-helper")
        if packaged_helper.exists():
            return ["pkexec", str(packaged_helper)]
        return ["pkexec", os.environ.get("PYTHON", shutil.which("python3") or "python3"), "-m", "laravel_installer.privileged_helper"]

    def run_operation(self, operation: str, payload: dict[str, object]) -> CommandResult:
        command = [*self.helper_command, operation]
        completed = subprocess.run(
            command,
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=False,
        )
        result = CommandResult(
            command=command,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
        if completed.returncode != 0:
            raise RuntimeError(summarize_output(completed.stderr or completed.stdout or "Privileged operation failed."))
        return result

    def run_operations(self, operations: list[dict[str, object]]) -> CommandResult:
        return self.run_operation("run_operations", {"operations": operations})

    def install_packages(self, packages: Iterable[str]) -> CommandResult:
        return self.run_operation("install_packages", {"packages": list(packages)})

    def write_vhost(self, site_name: str, content: str) -> CommandResult:
        return self.run_operation("write_vhost", {"site_name": site_name, "content": content})

    def enable_site(self, site_name: str) -> CommandResult:
        return self.run_operation("enable_site", {"site_name": site_name})

    def reload_apache(self) -> CommandResult:
        return self.run_operation("reload_apache", {})

    def ensure_hosts_entry(self, hostname: str) -> CommandResult:
        return self.run_operation("ensure_hosts_entry", {"hostname": hostname})

    def link_public_dir(self, source: str, destination: str) -> CommandResult:
        return self.run_operation("link_public_dir", {"source": source, "destination": destination})

    def set_permissions(self, path: str, username: str) -> CommandResult:
        return self.run_operation("set_permissions", {"path": path, "username": username})

    def ensure_directory_owner(self, path: str, username: str) -> CommandResult:
        return self.run_operation("ensure_directory_owner", {"path": path, "username": username})

    def configure_apache_php(self, php_version: str) -> CommandResult:
        return self.run_operation("configure_apache_php", {"php_version": php_version})

    def ensure_service_running(self, service_name: str) -> CommandResult:
        return self.run_operation("ensure_service_running", {"service_name": service_name})
