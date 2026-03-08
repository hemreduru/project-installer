from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .constants import DEFAULT_BASE_DIR, DEFAULT_HOST_SUFFIX


@dataclass
class ProjectConfig:
    name: str
    repo_url: str
    hostname: str = ""
    target_dir: str = ""
    enabled: bool = True

    def normalized_hostname(self) -> str:
        return self.hostname.strip() or f"{self.name}{DEFAULT_HOST_SUFFIX}"

    def normalized_target_dir(self) -> Path:
        return Path(self.target_dir.strip() or str(DEFAULT_BASE_DIR / self.name))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectConfig":
        return cls(
            name=str(data.get("name", "")).strip(),
            repo_url=str(data.get("repo_url", "")).strip(),
            hostname=str(data.get("hostname", "")).strip(),
            target_dir=str(data.get("target_dir", "")).strip(),
            enabled=bool(data.get("enabled", True)),
        )


@dataclass
class AppConfig:
    projects: list[ProjectConfig] = field(default_factory=list)
    default_base_dir: str = str(DEFAULT_BASE_DIR)
    last_used_php: str = ""
    ui_preferences: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "projects": [project.to_dict() for project in self.projects],
            "default_base_dir": self.default_base_dir,
            "last_used_php": self.last_used_php,
            "ui_preferences": self.ui_preferences,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppConfig":
        projects = [ProjectConfig.from_dict(item) for item in data.get("projects", [])]
        return cls(
            projects=[project for project in projects if project.name and project.repo_url],
            default_base_dir=str(data.get("default_base_dir", DEFAULT_BASE_DIR)),
            last_used_php=str(data.get("last_used_php", "")).strip(),
            ui_preferences=dict(data.get("ui_preferences", {})),
        )


@dataclass
class CommandResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str


@dataclass
class StepResult:
    project_name: str
    step: str
    status: str
    summary: str
    stdout: str = ""
    stderr: str = ""
    retryable: bool = False
    user_action_required: str = ""


@dataclass
class ProjectExecution:
    project: ProjectConfig
    steps: list[StepResult] = field(default_factory=list)

    @property
    def failed(self) -> bool:
        return any(step.status == "failed" for step in self.steps)
