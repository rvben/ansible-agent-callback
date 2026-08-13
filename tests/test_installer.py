"""Tests for the plugin installer."""

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ansible_agent_callback import installer


class TestInstallPlugin:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.install_dir = os.path.join(self.tmpdir, ".ansible", "plugins", "callback")

    def teardown_method(self):
        shutil.rmtree(self.tmpdir)

    def test_install_creates_directory_and_copies_plugin(self):
        result = installer.install_plugin(self.install_dir)
        assert os.path.isfile(os.path.join(self.install_dir, "agent.py"))
        assert "Installed" in result

    def test_install_is_idempotent(self):
        installer.install_plugin(self.install_dir)
        result = installer.install_plugin(self.install_dir)
        assert os.path.isfile(os.path.join(self.install_dir, "agent.py"))
        assert "Installed" in result

    def test_uninstall_removes_plugin(self):
        installer.install_plugin(self.install_dir)
        result = installer.uninstall_plugin(self.install_dir)
        assert not os.path.isfile(os.path.join(self.install_dir, "agent.py"))
        assert "Removed" in result

    def test_uninstall_missing_is_noop(self):
        result = installer.uninstall_plugin(self.install_dir)
        assert "not found" in result.lower()

    def test_plugin_path_returns_default(self):
        path = installer.default_install_dir()
        assert path.endswith(os.path.join(".ansible", "plugins", "callback"))
