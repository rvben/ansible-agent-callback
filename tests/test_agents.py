"""Tests for agent configuration modules."""

import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ansible_agent_callback.agents import (
    claude_code,
    codex_cli,
    gemini_cli,
    shell,
    ansible_cfg,
)

ENV_KEY = "ANSIBLE_STDOUT_CALLBACK"
ENV_VAL = "agent"


class TestClaudeCode:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.config_dir = os.path.join(self.tmpdir, ".claude")
        os.makedirs(self.config_dir)
        self.settings_path = os.path.join(self.config_dir, "settings.json")

    def teardown_method(self):
        shutil.rmtree(self.tmpdir)

    def test_detect_true_when_dir_exists(self):
        assert claude_code._detect(self.config_dir)

    def test_detect_false_when_missing(self):
        assert not claude_code._detect(os.path.join(self.tmpdir, "nonexistent"))

    def test_configure_creates_env_key(self):
        with open(self.settings_path, "w") as f:
            json.dump({"env": {}}, f)
        claude_code._configure(self.settings_path)
        with open(self.settings_path) as f:
            data = json.load(f)
        assert data["env"][ENV_KEY] == ENV_VAL

    def test_configure_creates_env_section(self):
        with open(self.settings_path, "w") as f:
            json.dump({}, f)
        claude_code._configure(self.settings_path)
        with open(self.settings_path) as f:
            data = json.load(f)
        assert data["env"][ENV_KEY] == ENV_VAL

    def test_configure_creates_file_if_missing(self):
        claude_code._configure(self.settings_path)
        with open(self.settings_path) as f:
            data = json.load(f)
        assert data["env"][ENV_KEY] == ENV_VAL

    def test_configure_preserves_existing_keys(self):
        with open(self.settings_path, "w") as f:
            json.dump({"env": {"OTHER": "value"}, "otherKey": True}, f)
        claude_code._configure(self.settings_path)
        with open(self.settings_path) as f:
            data = json.load(f)
        assert data["env"]["OTHER"] == "value"
        assert data["otherKey"] is True
        assert data["env"][ENV_KEY] == ENV_VAL

    def test_configure_is_idempotent(self):
        claude_code._configure(self.settings_path)
        claude_code._configure(self.settings_path)
        with open(self.settings_path) as f:
            data = json.load(f)
        assert data["env"][ENV_KEY] == ENV_VAL

    def test_is_configured_true(self):
        with open(self.settings_path, "w") as f:
            json.dump({"env": {ENV_KEY: ENV_VAL}}, f)
        assert claude_code._is_configured(self.settings_path)

    def test_is_configured_false(self):
        with open(self.settings_path, "w") as f:
            json.dump({"env": {}}, f)
        assert not claude_code._is_configured(self.settings_path)

    def test_unconfigure_removes_key(self):
        with open(self.settings_path, "w") as f:
            json.dump({"env": {ENV_KEY: ENV_VAL, "OTHER": "val"}}, f)
        claude_code._unconfigure(self.settings_path)
        with open(self.settings_path) as f:
            data = json.load(f)
        assert ENV_KEY not in data["env"]
        assert data["env"]["OTHER"] == "val"


class TestCodexCli:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.config_dir = os.path.join(self.tmpdir, ".codex")
        os.makedirs(self.config_dir)
        self.config_path = os.path.join(self.config_dir, "config.toml")

    def teardown_method(self):
        shutil.rmtree(self.tmpdir)

    def test_detect_true_when_dir_exists(self):
        assert codex_cli._detect(self.config_dir)

    def test_detect_false_when_missing(self):
        assert not codex_cli._detect(os.path.join(self.tmpdir, "nonexistent"))

    def test_configure_creates_file_with_env(self):
        codex_cli._configure(self.config_path)
        with open(self.config_path) as f:
            content = f.read()
        assert "ANSIBLE_STDOUT_CALLBACK" in content
        assert '"agent"' in content

    def test_configure_appends_to_existing(self):
        with open(self.config_path, "w") as f:
            f.write('[model]\nname = "gpt-4"\n')
        codex_cli._configure(self.config_path)
        with open(self.config_path) as f:
            content = f.read()
        assert 'name = "gpt-4"' in content
        assert "ANSIBLE_STDOUT_CALLBACK" in content

    def test_configure_is_idempotent(self):
        codex_cli._configure(self.config_path)
        codex_cli._configure(self.config_path)
        with open(self.config_path) as f:
            content = f.read()
        assert content.count("ANSIBLE_STDOUT_CALLBACK") == 1

    def test_is_configured_true(self):
        codex_cli._configure(self.config_path)
        assert codex_cli._is_configured(self.config_path)

    def test_is_configured_false_when_missing(self):
        assert not codex_cli._is_configured(self.config_path)

    def test_unconfigure_removes_line(self):
        codex_cli._configure(self.config_path)
        codex_cli._unconfigure(self.config_path)
        with open(self.config_path) as f:
            content = f.read()
        assert "ANSIBLE_STDOUT_CALLBACK" not in content


class TestGeminiCli:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.config_dir = os.path.join(self.tmpdir, ".gemini")
        os.makedirs(self.config_dir)
        self.env_path = os.path.join(self.config_dir, ".env")

    def teardown_method(self):
        shutil.rmtree(self.tmpdir)

    def test_detect_true_when_dir_exists(self):
        assert gemini_cli._detect(self.config_dir)

    def test_configure_creates_env_file(self):
        gemini_cli._configure(self.env_path)
        with open(self.env_path) as f:
            content = f.read()
        assert f"{ENV_KEY}={ENV_VAL}" in content
        assert "# ansible-agent-callback" in content

    def test_configure_appends_to_existing(self):
        with open(self.env_path, "w") as f:
            f.write("OTHER_VAR=value\n")
        gemini_cli._configure(self.env_path)
        with open(self.env_path) as f:
            content = f.read()
        assert "OTHER_VAR=value" in content
        assert f"{ENV_KEY}={ENV_VAL}" in content

    def test_configure_is_idempotent(self):
        gemini_cli._configure(self.env_path)
        gemini_cli._configure(self.env_path)
        with open(self.env_path) as f:
            content = f.read()
        assert content.count(ENV_KEY) == 1

    def test_unconfigure_removes_marked_lines(self):
        with open(self.env_path, "w") as f:
            f.write("OTHER=val\n")
        gemini_cli._configure(self.env_path)
        gemini_cli._unconfigure(self.env_path)
        with open(self.env_path) as f:
            content = f.read()
        assert ENV_KEY not in content
        assert "OTHER=val" in content


class TestShellProfile:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.zshrc = os.path.join(self.tmpdir, ".zshrc")

    def teardown_method(self):
        shutil.rmtree(self.tmpdir)

    def test_detect_zshrc(self):
        open(self.zshrc, "w").close()
        assert shell._detect(self.zshrc, None)

    def test_detect_bashrc_fallback(self):
        bashrc = os.path.join(self.tmpdir, ".bashrc")
        open(bashrc, "w").close()
        assert shell._detect(None, bashrc)

    def test_configure_appends_export(self):
        open(self.zshrc, "w").close()
        shell._configure(self.zshrc)
        with open(self.zshrc) as f:
            content = f.read()
        assert f"export {ENV_KEY}={ENV_VAL}" in content
        assert "# ansible-agent-callback" in content

    def test_configure_is_idempotent(self):
        open(self.zshrc, "w").close()
        shell._configure(self.zshrc)
        shell._configure(self.zshrc)
        with open(self.zshrc) as f:
            content = f.read()
        assert content.count(ENV_KEY) == 1

    def test_unconfigure_removes_marked_lines(self):
        with open(self.zshrc, "w") as f:
            f.write("# existing stuff\n")
        shell._configure(self.zshrc)
        shell._unconfigure(self.zshrc)
        with open(self.zshrc) as f:
            content = f.read()
        assert ENV_KEY not in content
        assert "existing stuff" in content


class TestAnsibleCfg:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.cfg_path = os.path.join(self.tmpdir, ".ansible.cfg")

    def teardown_method(self):
        shutil.rmtree(self.tmpdir)

    def test_detect_always_true(self):
        assert ansible_cfg._detect()

    def test_configure_creates_file(self):
        ansible_cfg._configure(self.cfg_path)
        with open(self.cfg_path) as f:
            content = f.read()
        assert "stdout_callback = agent" in content
        assert "[defaults]" in content

    def test_configure_adds_to_existing(self):
        with open(self.cfg_path, "w") as f:
            f.write("[defaults]\nhost_key_checking = False\n")
        ansible_cfg._configure(self.cfg_path)
        with open(self.cfg_path) as f:
            content = f.read()
        assert "host_key_checking = False" in content
        assert "stdout_callback = agent" in content

    def test_configure_is_idempotent(self):
        ansible_cfg._configure(self.cfg_path)
        ansible_cfg._configure(self.cfg_path)
        with open(self.cfg_path) as f:
            content = f.read()
        assert content.count("stdout_callback") == 1

    def test_is_configured_true(self):
        ansible_cfg._configure(self.cfg_path)
        assert ansible_cfg._is_configured(self.cfg_path)

    def test_is_configured_false(self):
        assert not ansible_cfg._is_configured(self.cfg_path)

    def test_unconfigure_removes_line(self):
        with open(self.cfg_path, "w") as f:
            f.write("[defaults]\nhost_key_checking = False\n")
        ansible_cfg._configure(self.cfg_path)
        ansible_cfg._unconfigure(self.cfg_path)
        with open(self.cfg_path) as f:
            content = f.read()
        assert "stdout_callback" not in content
        assert "host_key_checking = False" in content
