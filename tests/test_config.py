import json
import tempfile
import unittest
from pathlib import Path

from laravel_installer.config import ConfigStore
from laravel_installer.models import AppConfig, ProjectConfig


class ConfigStoreTests(unittest.TestCase):
    def test_save_and_load_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            store = ConfigStore(path)
            original = AppConfig(
                projects=[ProjectConfig(name="shop", repo_url="git@example.com:shop.git", hostname="shop.test", target_dir="/var/www/shop")],
                default_base_dir="/srv/www",
                last_used_php="8.3",
                ui_preferences={"view": "logs"},
            )
            store.save(original)
            loaded = store.load()
            self.assertEqual(loaded.to_dict(), original.to_dict())

    def test_invalid_json_returns_default_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text("{bad json", encoding="utf-8")
            store = ConfigStore(path)
            loaded = store.load()
            self.assertEqual(loaded.to_dict(), AppConfig().to_dict())


if __name__ == "__main__":
    unittest.main()
