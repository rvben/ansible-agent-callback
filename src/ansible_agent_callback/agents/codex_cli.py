"""Codex CLI agent configuration (~/.codex/config.toml)."""

from __future__ import annotations

import os
from pathlib import Path

NAME = "Codex CLI"
SLUG = "codex-cli"
CONFIG_PATH = "~/.codex/config.toml"

_ENV_KEY = "ANSIBLE_STDOUT_CALLBACK"
_ENV_VAL = "agent"
_MARKER = "# ansible-agent-callback"
_LINE = f'{_ENV_KEY} = "{_ENV_VAL}"  {_MARKER}'
_SECTION_HEADER = "[shell_environment_policy.set]"


def _default_dir():
    return str(Path.home() / ".codex")


def _default_path():
    return str(Path.home() / ".codex" / "config.toml")


def _detect(config_dir: str | None = None) -> bool:
    return os.path.isdir(config_dir or _default_dir())


def _is_configured(config_path: str | None = None) -> bool:
    path = config_path or _default_path()
    if not os.path.isfile(path):
        return False
    with open(path) as f:
        return _ENV_KEY in f.read()


def _configure(config_path: str | None = None) -> str:
    path = config_path or _default_path()
    if os.path.isfile(path):
        with open(path) as f:
            content = f.read()
        if _ENV_KEY in content:
            return f"{NAME} already configured"
        if _SECTION_HEADER in content:
            content = content.replace(_SECTION_HEADER, f"{_SECTION_HEADER}\n{_LINE}")
        else:
            content = content.rstrip() + f"\n\n{_SECTION_HEADER}\n{_LINE}\n"
    else:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        content = f"{_SECTION_HEADER}\n{_LINE}\n"
    with open(path, "w") as f:
        f.write(content)
    return f"Configured {NAME}"


def _unconfigure(config_path: str | None = None) -> str:
    path = config_path or _default_path()
    if not os.path.isfile(path):
        return f"{NAME} not configured"
    with open(path) as f:
        lines = f.readlines()
    lines = [l for l in lines if _ENV_KEY not in l]
    content = "".join(lines)
    if _SECTION_HEADER in content:
        section_idx = content.index(_SECTION_HEADER)
        after = content[section_idx + len(_SECTION_HEADER):].lstrip("\n")
        if not after or after.startswith("["):
            content = content[:section_idx] + after
    with open(path, "w") as f:
        f.write(content)
    return f"Unconfigured {NAME}"


def detect() -> bool:
    return _detect()


def is_configured() -> bool:
    return _is_configured()


def configure() -> str:
    return _configure()


def unconfigure() -> str:
    return _unconfigure()
