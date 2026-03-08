from pathlib import Path

APP_NAME = "Laravel Installer"
APP_SLUG = "laravel-installer"
APP_VERSION = "1.0.1"

COLOR_BG = "#1e1e1e"
COLOR_SIDEBAR = "#252526"
COLOR_CARD = "#2d2d2d"
COLOR_PRIMARY = "#3b8ed0"
COLOR_SUCCESS = "#10b981"
COLOR_WARNING = "#f59e0b"
COLOR_DANGER = "#ef4444"
COLOR_TEXT = "#e1e1e1"
COLOR_TEXT_DIM = "#a1a1a1"

CONFIG_DIR = Path.home() / ".config" / APP_SLUG
CONFIG_PATH = CONFIG_DIR / "config.json"
DEFAULT_BASE_DIR = Path("/var/www")
DEFAULT_HOST_SUFFIX = ".test"
DEFAULT_HTML_DIR = Path("/var/www/html")
SUPPORTED_UBUNTU_VERSIONS = ("22.04", "24.04")

PHP_EXTENSIONS_REQUIRED = (
    "bcmath",
    "curl",
    "dom",
    "gd",
    "mbstring",
    "mysql",
    "sqlite3",
    "xml",
    "zip",
)

SYSTEM_PACKAGES = (
    "git",
    "composer",
    "apache2",
    "pkexec",
)
