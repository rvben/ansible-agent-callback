"""Tests for the CLI."""

import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from unittest.mock import patch

from ansible_agent_callback import cli


class TestEnvCommand:
    def test_env_prints_export(self, capsys):
        cli.cmd_env([])
        captured = capsys.readouterr()
        assert captured.out.strip() == "export ANSIBLE_STDOUT_CALLBACK=agent"

    def test_env_json_is_structured(self, capsys):
        cli.cmd_env([], output="json")
        assert json.loads(capsys.readouterr().out) == {
            "export": "export ANSIBLE_STDOUT_CALLBACK=agent"
        }


class TestIntrospectionCommands:
    def test_schema_is_clispec_v03_with_flat_commands(self):
        document = cli.schema_document()
        assert document["clispec"] == "0.3"
        assert document["$schema"] == "https://clispec.dev/schema/v0.3.json"
        assert document["output"] == {"tty": "text", "piped": "json"}
        assert all("subcommands" not in command for command in document["commands"])
        assert all("effects" in command for command in document["commands"])

    def test_capabilities_json_is_offline_and_structured(self, capsys):
        cli.cmd_capabilities([], output="json")
        document = json.loads(capsys.readouterr().out)
        assert document["name"] == "ansible-agent-callback"
        assert document["clispec"] == "0.3"

    def test_global_output_flag_can_follow_subcommand(self, capsys):
        with patch.object(
            sys,
            "argv",
            ["ansible-agent-callback", "capabilities", "--output", "text"],
        ):
            cli.main()
        assert "clispec 0.3" in capsys.readouterr().out


class TestInstallCommand:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.install_dir = os.path.join(self.tmpdir, "callback")

    def teardown_method(self):
        shutil.rmtree(self.tmpdir)

    def test_install_plugin_only(self):
        cli.cmd_install(["--plugin-only"], install_dir=self.install_dir)
        assert os.path.isfile(os.path.join(self.install_dir, "agent.py"))

    def test_install_plugin_only_json(self, capsys):
        cli.cmd_install(["--plugin-only"], install_dir=self.install_dir, output="json")
        document = json.loads(capsys.readouterr().out)
        assert document["installed"] is True
        assert document["configured_agents"] == []

    def test_install_with_specific_agents(self):
        config_dir = os.path.join(self.tmpdir, ".claude")
        os.makedirs(config_dir)
        settings_path = os.path.join(config_dir, "settings.json")
        with (
            patch(
                "ansible_agent_callback.agents.claude_code._default_dir",
                return_value=config_dir,
            ),
            patch(
                "ansible_agent_callback.agents.claude_code._default_path",
                return_value=settings_path,
            ),
        ):
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
        cli.cmd_uninstall([], install_dir=self.install_dir)
        assert not os.path.isfile(os.path.join(self.install_dir, "agent.py"))
