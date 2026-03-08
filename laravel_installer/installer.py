from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from packaging.version import InvalidVersion, Version

from .constants import DEFAULT_HTML_DIR, PHP_EXTENSIONS_REQUIRED, SYSTEM_PACKAGES, SUPPORTED_UBUNTU_VERSIONS
from .models import ProjectConfig, ProjectExecution, StepResult
from .system import CommandRunner, EnvironmentInspector, PrivilegedOperations
from .utils import normalize_hostname, normalize_target_dir, slugify_project_name, summarize_output


class InstallerService:
    def __init__(
        self,
        runner: CommandRunner | None = None,
        inspector: EnvironmentInspector | None = None,
        privileged: PrivilegedOperations | None = None,
    ) -> None:
        self.runner = runner or CommandRunner()
        self.inspector = inspector or EnvironmentInspector(self.runner)
        self.privileged = privileged or PrivilegedOperations()

    def validate_project(self, project: ProjectConfig, default_base_dir: str) -> ProjectConfig:
        project_name = slugify_project_name(project.name)
        if not project_name:
            raise ValueError("Project name is required.")
        hostname = normalize_hostname(project.hostname, project_name)
        target_dir = normalize_target_dir(project.target_dir, project_name, default_base_dir)
        if not project.repo_url.strip():
            raise ValueError("Repository URL is required.")
        return ProjectConfig(
            name=project_name,
            repo_url=project.repo_url.strip(),
            hostname=hostname,
            target_dir=str(target_dir),
            enabled=project.enabled,
        )

    def build_preflight_summary(self, projects: list[ProjectConfig], default_base_dir: str) -> str:
        snapshot = self.inspector.preflight_snapshot()
        lines = [
            f"Ubuntu version: {snapshot['ubuntu_version'] or 'unknown'}",
            f"Installed PHP versions: {', '.join(snapshot['php_versions']) or 'none'}",
            f"git/composer/apache2/pkexec: "
            f"{'yes' if snapshot['git'] else 'no'}/"
            f"{'yes' if snapshot['composer'] else 'no'}/"
            f"{'yes' if snapshot['apache2'] else 'no'}/"
            f"{'yes' if snapshot['pkexec'] else 'no'}",
            "",
            "Projects:",
        ]
        for project in projects:
            valid = self.validate_project(project, default_base_dir)
            lines.append(
                f"- {valid.name}: host={valid.hostname}, target={valid.target_dir}, html={DEFAULT_HTML_DIR / valid.name}"
            )
        missing = self.required_system_packages(snapshot)
        if missing:
            lines.extend(["", f"Packages to install: {', '.join(missing)}"])
        return "\n".join(lines)

    def required_system_packages(self, snapshot: dict[str, object]) -> list[str]:
        missing: list[str] = []
        for package in SYSTEM_PACKAGES:
            if package == "pkexec":
                if not snapshot.get("pkexec"):
                    missing.append("policykit-1")
                continue
            if not snapshot.get(package):
                missing.append(package)
        ubuntu_version = str(snapshot.get("ubuntu_version", ""))
        if ubuntu_version and ubuntu_version not in SUPPORTED_UBUNTU_VERSIONS:
            missing.append("Unsupported Ubuntu release")
        return missing

    def detect_php_version(self, composer_json_path: Path) -> str:
        if not composer_json_path.exists():
            return "8.2"
        with composer_json_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        constraint = str(data.get("require", {}).get("php", "")).strip()
        if not constraint:
            return "8.2"
        options = []
        for part in constraint.split("||"):
            version = self._extract_minimum_version(part.strip())
            if version:
                options.append(version)
        if not options:
            return "8.2"
        return str(sorted(options, key=Version)[0])

    def _extract_minimum_version(self, constraint: str) -> str | None:
        tokens = [token.strip() for token in constraint.replace(",", " ").split() if token.strip()]
        candidates: list[Version] = []
        for token in tokens:
            if token.startswith("^") or token.startswith("~"):
                raw = token[1:]
            elif token.startswith(">=") or token.startswith("=="):
                raw = token[2:]
            elif token.startswith(">"):
                raw = token[1:]
            elif token.startswith("="):
                raw = token[1:]
            elif token.startswith("*"):
                continue
            elif token[0].isdigit():
                raw = token
            else:
                continue
            raw = raw.replace(".*", ".0")
            try:
                parsed = Version(raw)
            except InvalidVersion:
                continue
            candidates.append(parsed)
        if not candidates:
            return None
        selected = sorted(candidates)[0]
        return f"{selected.major}.{selected.minor}"

    def extension_packages_for_php(self, php_version: str) -> list[str]:
        return [f"php{php_version}-{extension}" for extension in PHP_EXTENSIONS_REQUIRED]

    def execute_projects(
        self,
        projects: list[ProjectConfig],
        default_base_dir: str,
        log_callback,
    ) -> list[ProjectExecution]:
        executions: list[ProjectExecution] = []
        snapshot = self.inspector.preflight_snapshot()
        missing_system = self.required_system_packages(snapshot)
        apt_packages = [pkg for pkg in missing_system if not pkg.startswith("Unsupported")]
        if apt_packages:
            log_callback("Installing missing system packages via pkexec...", "info")
            self.privileged.install_packages(apt_packages)
        for project in projects:
            valid = self.validate_project(project, default_base_dir)
            execution = ProjectExecution(project=valid)
            executions.append(execution)
            log_callback(f"Starting {valid.name}", "info")
            try:
                self._execute_project(valid, execution, log_callback)
            except Exception as exc:
                execution.steps.append(
                    StepResult(
                        project_name=valid.name,
                        step="project",
                        status="failed",
                        summary=str(exc),
                        stderr=str(exc),
                        retryable=True,
                        user_action_required="Review logs and retry the failed project.",
                    )
                )
                log_callback(f"{valid.name}: {exc}", "error")
        return executions

    def _execute_project(self, project: ProjectConfig, execution: ProjectExecution, log_callback) -> None:
        project_dir = Path(project.target_dir)
        html_dir = DEFAULT_HTML_DIR / project.name

        if not project_dir.exists():
            result = self.runner.run(["git", "clone", project.repo_url, str(project_dir)])
            self._record(execution, "git_clone", "completed", "Repository cloned.", result.stdout, result.stderr)
        else:
            result = self.runner.run(["git", "-C", str(project_dir), "pull"])
            self._record(execution, "git_pull", "completed", "Repository updated.", result.stdout, result.stderr)
        log_callback(f"{project.name}: source ready", "success")

        env_example = project_dir / ".env.example"
        env_file = project_dir / ".env"
        if env_example.exists() and not env_file.exists():
            shutil.copy2(env_example, env_file)
            self._record(execution, "env", "completed", ".env created from .env.example")

        php_version = self.detect_php_version(project_dir / "composer.json")
        installed_versions = self.inspector.installed_php_versions()
        if php_version not in installed_versions:
            self.privileged.install_packages([f"php{php_version}", f"php{php_version}-fpm", *self.extension_packages_for_php(php_version)])
            installed_versions = self.inspector.installed_php_versions()
        else:
            missing_extensions = [
                package for package in self.extension_packages_for_php(php_version)
                if not Path("/usr/bin/dpkg-query").exists() or self._is_package_missing(package)
            ]
            if missing_extensions:
                self.privileged.install_packages(missing_extensions)
        self._record(execution, "php", "completed", f"Using PHP {php_version}")

        php_bin = shutil.which(f"php{php_version}") or f"/usr/bin/php{php_version}"
        composer_bin = shutil.which("composer") or "/usr/bin/composer"
        result = self.runner.run([php_bin, composer_bin, "install", "-d", str(project_dir)])
        self._record(
            execution,
            "composer",
            "completed",
            "Composer dependencies installed.",
            result.stdout,
            result.stderr,
        )
        log_callback(f"{project.name}: composer install finished", "success")

        vhost = self.render_vhost(project.hostname, html_dir, php_version)
        self.privileged.link_public_dir(str(project_dir / "public"), str(html_dir))
        self.privileged.set_permissions(str(project_dir), self._current_username())
        self.privileged.ensure_hosts_entry(project.hostname)
        self.privileged.write_vhost(project.name, vhost)
        self.privileged.enable_site(project.name)
        self.privileged.reload_apache()
        self._record(execution, "publish", "completed", f"Published at http://{project.hostname}")
        log_callback(f"{project.name}: published at http://{project.hostname}", "success")

    def render_vhost(self, hostname: str, document_root: Path, php_version: str) -> str:
        template_path = Path(__file__).with_name("templates") / "apache_vhost.conf"
        template = template_path.read_text(encoding="utf-8")
        return template.format(hostname=hostname, document_root=document_root, php_version=php_version)

    def _current_username(self) -> str:
        return os.environ.get("SUDO_USER") or os.environ.get("USER") or "www-data"

    def _is_package_missing(self, package_name: str) -> bool:
        try:
            result = self.runner.run(["dpkg-query", "-W", "-f=${Status}", package_name], check=False)
        except RuntimeError:
            return True
        return "install ok installed" not in result.stdout

    def _record(self, execution: ProjectExecution, step: str, status: str, summary: str, stdout: str = "", stderr: str = "") -> None:
        execution.steps.append(
            StepResult(
                project_name=execution.project.name,
                step=step,
                status=status,
                summary=summary,
                stdout=summarize_output(stdout),
                stderr=summarize_output(stderr),
            )
        )
