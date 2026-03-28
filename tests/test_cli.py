"""Tests for the CLI."""

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from unittest.mock import patch
from ansible_agent_callback import cli


class TestEnvCommand:
    def test_env_prints_export(self, capsys):
        cli.cmd_env([])
        captured = capsys.readouterr()
        assert captured.out.strip() == "export ANSIBLE_STDOUT_CALLBACK=agent"


class TestInstallCommand:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.install_dir = os.path.join(self.tmpdir, "callback")

    def teardown_method(self):
        shutil.rmtree(self.tmpdir)

    def test_install_plugin_only(self):
        cli.cmd_install(["--plugin-only"], install_dir=self.install_dir)
        assert os.path.isfile(os.path.join(self.install_dir, "agent.py"))

    def test_install_with_specific_agents(self):
        config_dir = os.path.join(self.tmpdir, ".claude")
        os.makedirs(config_dir)
        settings_path = os.path.join(config_dir, "settings.json")
        with patch("ansible_agent_callback.agents.claude_code._default_dir", return_value=config_dir), \
             patch("ansible_agent_callback.agents.claude_code._default_path", return_value=settings_path):
            cli.cmd_install(["--agents", "claude-code"], install_dir=self.install_dir)
        assert os.path.isfile(os.path.join(self.install_dir, "agent.py"))


class TestUninstallCommand:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.install_dir = os.path.join(self.tmpdir, "callback")

    def teardown_method(self):
        shutil.rmtree(self.tmpdir)

    def test_uninstall_removes_plugin(self):
        cli.cmd_install(["--plugin-only"], install_dir=self.install_dir)
        cli.cmd_uninstall(["--all"], install_dir=self.install_dir)
        assert not os.path.isfile(os.path.join(self.install_dir, "agent.py"))
