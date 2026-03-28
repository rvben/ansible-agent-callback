"""Ansible global config (~/.ansible.cfg)."""

from __future__ import annotations

import configparser
import os
from pathlib import Path

NAME = "Ansible global"
SLUG = "ansible"
CONFIG_PATH = "~/.ansible.cfg"

_SECTION = "defaults"
_KEY = "stdout_callback"
_VAL = "agent"


def _default_path():
    return str(Path.home() / ".ansible.cfg")


def _detect() -> bool:
    return True


def _is_configured(cfg_path: str | None = None) -> bool:
    path = cfg_path or _default_path()
    if not os.path.isfile(path):
        return False
    config = configparser.ConfigParser()
    config.read(path)
    return config.get(_SECTION, _KEY, fallback=None) == _VAL


def _configure(cfg_path: str | None = None) -> str:
    path = cfg_path or _default_path()
    config = configparser.ConfigParser()
    if os.path.isfile(path):
        config.read(path)
    if not config.has_section(_SECTION):
        config.add_section(_SECTION)
    if config.get(_SECTION, _KEY, fallback=None) == _VAL:
        return f"{NAME} already configured"
    config.set(_SECTION, _KEY, _VAL)
    with open(path, "w") as f:
        config.write(f)
    return f"Configured {NAME}"


def _unconfigure(cfg_path: str | None = None) -> str:
    path = cfg_path or _default_path()
    if not os.path.isfile(path):
        return f"{NAME} not configured"
    config = configparser.ConfigParser()
    config.read(path)
    if config.has_option(_SECTION, _KEY):
        config.remove_option(_SECTION, _KEY)
        with open(path, "w") as f:
            config.write(f)
    return f"Unconfigured {NAME}"


def detect() -> bool:
    return _detect()


def is_configured() -> bool:
    return _is_configured()


def configure() -> str:
    return _configure()


def unconfigure() -> str:
    return _unconfigure()
