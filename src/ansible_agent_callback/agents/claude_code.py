"""Claude Code agent configuration (~/.claude/settings.json)."""

from __future__ import annotations

import json
import os
from pathlib import Path

NAME = "Claude Code"
SLUG = "claude-code"
CONFIG_PATH = "~/.claude/settings.json"

_ENV_KEY = "ANSIBLE_STDOUT_CALLBACK"
_ENV_VAL = "agent"


def _default_dir():
    return str(Path.home() / ".claude")


def _default_path():
    return str(Path.home() / ".claude" / "settings.json")


def _detect(config_dir: str | None = None) -> bool:
    return os.path.isdir(config_dir or _default_dir())


def _is_configured(settings_path: str | None = None) -> bool:
    path = settings_path or _default_path()
    if not os.path.isfile(path):
        return False
    with open(path) as f:
        data = json.load(f)
    return data.get("env", {}).get(_ENV_KEY) == _ENV_VAL


def _configure(settings_path: str | None = None) -> str:
    path = settings_path or _default_path()
    if os.path.isfile(path):
        with open(path) as f:
            data = json.load(f)
    else:
        data = {}
    if "env" not in data:
        data["env"] = {}
    data["env"][_ENV_KEY] = _ENV_VAL
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    return f"Configured {NAME}"


def _unconfigure(settings_path: str | None = None) -> str:
    path = settings_path or _default_path()
    if not os.path.isfile(path):
        return f"{NAME} not configured"
    with open(path) as f:
        data = json.load(f)
    data.get("env", {}).pop(_ENV_KEY, None)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    return f"Unconfigured {NAME}"


def detect() -> bool:
    return _detect()


def is_configured() -> bool:
    return _is_configured()


def configure() -> str:
    return _configure()


def unconfigure() -> str:
    return _unconfigure()
