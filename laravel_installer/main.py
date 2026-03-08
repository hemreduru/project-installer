from __future__ import annotations

import importlib
import subprocess
import sys


def ensure_runtime_dependencies() -> None:
    missing = []
    for package in ("customtkinter", "packaging"):
        try:
            importlib.import_module(package)
        except ImportError:
            missing.append(package)
    if missing:
        subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])


def main() -> None:
    ensure_runtime_dependencies()
    from .ui import run_app

    run_app()


if __name__ == "__main__":
    main()
