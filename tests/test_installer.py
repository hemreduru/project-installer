import json
import tempfile
import unittest
from pathlib import Path

from laravel_installer.installer import InstallerService
from laravel_installer.models import ProjectConfig


class InstallerServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = InstallerService()

    def test_detect_php_version_from_composer_constraints(self):
        with tempfile.TemporaryDirectory() as tmp:
            composer_path = Path(tmp) / "composer.json"
            composer_path.write_text(json.dumps({"require": {"php": "^8.2 || ^8.3"}}), encoding="utf-8")
            self.assertEqual(self.service.detect_php_version(composer_path), "8.2")

    def test_validate_project_normalizes_values(self):
        project = ProjectConfig(
            name="My API",
            repo_url=" git@github.com:org/repo.git ",
            hostname="",
            target_dir="",
        )
        normalized = self.service.validate_project(project, "/var/www")
        self.assertEqual(normalized.name, "my-api")
        self.assertEqual(normalized.hostname, "my-api.test")
        self.assertEqual(normalized.target_dir, "/var/www/my-api")


if __name__ == "__main__":
    unittest.main()
