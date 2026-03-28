"""Shell profile agent configuration (~/.zshrc or ~/.bashrc)."""

from __future__ import annotations

import os
from pathlib import Path

NAME = "Shell profile"
SLUG = "shell"
CONFIG_PATH = "~/.zshrc"

_ENV_KEY = "ANSIBLE_STDOUT_CALLBACK"
_ENV_VAL = "agent"
_MARKER = "# ansible-agent-callback"
_LINE = f"export {_ENV_KEY}={_ENV_VAL}  {_MARKER}"


def _default_zshrc():
    return str(Path.home() / ".zshrc")


def _default_bashrc():
    return str(Path.home() / ".bashrc")


def _find_profile():
    zshrc = _default_zshrc()
    if os.path.isfile(zshrc):
        return zshrc
    bashrc = _default_bashrc()
    if os.path.isfile(bashrc):
        return bashrc
    return None


def _detect(zshrc: str | None = None, bashrc: str | None = None) -> bool:
    zshrc = zshrc or _default_zshrc()
    bashrc = bashrc or _default_bashrc()
    return os.path.isfile(zshrc) or os.path.isfile(bashrc)


def _is_configured(profile_path: str | None = None) -> bool:
    path = profile_path or _find_profile()
    if not path or not os.path.isfile(path):
        return False
    with open(path) as f:
        return _MARKER in f.read()


def _configure(profile_path: str | None = None) -> str:
    path = profile_path or _find_profile()
    if not path:
        return "No shell profile found (~/.zshrc or ~/.bashrc)"
    with open(path) as f:
        content = f.read()
    if _MARKER in content:
        return f"{NAME} already configured"
    content = content.rstrip() + f"\n{_LINE}\n"
    with open(path, "w") as f:
        f.write(content)
    return f"Configured {NAME} ({path})"


def _unconfigure(profile_path: str | None = None) -> str:
    path = profile_path or _find_profile()
    if not path or not os.path.isfile(path):
        return f"{NAME} not configured"
    with open(path) as f:
        lines = f.readlines()
    lines = [l for l in lines if _MARKER not in l]
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
