"""Gemini CLI agent configuration (~/.gemini/.env)."""

from __future__ import annotations

import os
from pathlib import Path

NAME = "Gemini CLI"
SLUG = "gemini-cli"
CONFIG_PATH = "~/.gemini/.env"

_ENV_KEY = "ANSIBLE_STDOUT_CALLBACK"
_ENV_VAL = "agent"
_MARKER = "# ansible-agent-callback"
_LINE = f"{_ENV_KEY}={_ENV_VAL}  {_MARKER}"


def _default_dir():
    return str(Path.home() / ".gemini")


def _default_path():
    return str(Path.home() / ".gemini" / ".env")


def _detect(config_dir: str | None = None) -> bool:
    return os.path.isdir(config_dir or _default_dir())


def _is_configured(env_path: str | None = None) -> bool:
    path = env_path or _default_path()
    if not os.path.isfile(path):
        return False
    with open(path) as f:
        return _ENV_KEY in f.read()


def _configure(env_path: str | None = None) -> str:
    path = env_path or _default_path()
    if os.path.isfile(path):
        with open(path) as f:
            content = f.read()
        if _ENV_KEY in content:
            return f"{NAME} already configured"
        content = content.rstrip() + f"\n{_LINE}\n"
    else:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        content = f"{_LINE}\n"
    with open(path, "w") as f:
        f.write(content)
    return f"Configured {NAME}"


def _unconfigure(env_path: str | None = None) -> str:
    path = env_path or _default_path()
    if not os.path.isfile(path):
        return f"{NAME} not configured"
    with open(path) as f:
        lines = f.readlines()
    lines = [line for line in lines if _MARKER not in line]
    with open(path, "w") as f:
        f.write("".join(lines))
    return f"Unconfigured {NAME}"


def detect() -> bool:
    return _detect()


def is_configured() -> bool:
    return _is_configured()


def configure() -> str:
    return _configure()


def unconfigure() -> str:
    return _unconfigure()
