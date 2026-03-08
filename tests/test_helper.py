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

    @mock.patch("laravel_installer.privileged_helper.run")
    def test_ensure_directory_owner_creates_and_chowns_directory(self, run_mock):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "project"
            privileged_helper.ensure_directory_owner({"path": str(path), "username": "emre"})
            self.assertTrue(path.exists())
            run_mock.assert_any_call(["chown", "-R", "emre:emre", str(path)])
            run_mock.assert_any_call(["chmod", "775", str(path)])

    @mock.patch("laravel_installer.privileged_helper.run")
    @mock.patch("laravel_installer.privileged_helper.Path.exists", return_value=True)
    def test_configure_apache_php_enables_expected_modules(self, exists_mock, run_mock):
        privileged_helper.configure_apache_php({"php_version": "8.3"})
        run_mock.assert_any_call(["a2enmod", "proxy_fcgi"])
        run_mock.assert_any_call(["a2enmod", "setenvif"])
        run_mock.assert_any_call(["a2enmod", "rewrite"])
        run_mock.assert_any_call(["a2enconf", "php8.3-fpm"])
        run_mock.assert_any_call(["systemctl", "enable", "--now", "php8.3-fpm"])
        run_mock.assert_any_call(["systemctl", "enable", "--now", "apache2"])

    def test_run_operations_dispatches_batch(self):
        install_mock = mock.Mock()
        hosts_mock = mock.Mock()
        with mock.patch.dict(
            privileged_helper.OPERATIONS,
            {"install_packages": install_mock, "ensure_hosts_entry": hosts_mock},
            clear=False,
        ):
            privileged_helper.run_operations(
                {
                    "operations": [
                        {"operation": "install_packages", "payload": {"packages": ["git"]}},
                        {"operation": "ensure_hosts_entry", "payload": {"hostname": "demo.test"}},
                    ]
                }
            )
        install_mock.assert_called_once_with({"packages": ["git"]})
        hosts_mock.assert_called_once_with({"hostname": "demo.test"})


if __name__ == "__main__":
    unittest.main()
