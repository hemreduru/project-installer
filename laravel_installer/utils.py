from __future__ import annotations

import re
from pathlib import Path


def slugify_project_name(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9-]+", "-", value.strip().lower())
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-")
    return normalized


def normalize_hostname(value: str, project_name: str) -> str:
    raw = value.strip().lower() if value.strip() else f"{project_name}.test"
    if not re.fullmatch(r"[a-z0-9.-]+", raw):
        raise ValueError("Hostname may only contain lowercase letters, numbers, dots and hyphens.")
    return raw


def normalize_target_dir(value: str, project_name: str, default_base: str) -> Path:
    target = Path(value.strip()) if value.strip() else Path(default_base) / project_name
    if not str(target).startswith("/"):
        raise ValueError("Target directory must be an absolute path.")
    return target


def summarize_output(output: str, limit: int = 400) -> str:
    cleaned = " ".join(output.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3] + "..."
