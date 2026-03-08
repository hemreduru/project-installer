import tempfile
import unittest
from pathlib import Path
from unittest import mock

from laravel_installer import privileged_helper


class PrivilegedHelperTests(unittest.TestCase):
    def test_install_packages_validates_payload(self):
        with self.assertRaises(ValueError):
            privileged_helper.install_packages({"packages": "git"})

    def test_link_public_dir_replaces_existing_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            source.mkdir()
            destination = Path(tmp) / "dest"
            destination.symlink_to(source)
            privileged_helper.link_public_dir({"source": str(source), "destination": str(destination)})
            self.assertTrue(destination.is_symlink())

    @mock.patch("laravel_installer.privileged_helper.run")
    def test_set_permissions_executes_expected_commands(self, run_mock):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            privileged_helper.set_permissions({"path": str(path), "username": "emre"})
            run_mock.assert_any_call(["chmod", "-R", "775", str(path)])
            run_mock.assert_any_call(["chown", "-R", "www-data:emre", str(path)])


if __name__ == "__main__":
    unittest.main()
