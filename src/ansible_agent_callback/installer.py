"""Install/uninstall the agent callback plugin."""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def default_install_dir() -> str:
    return str(Path.home() / ".ansible" / "plugins" / "callback")


def _plugin_source() -> str:
    return str(Path(__file__).parent / "plugin.py")


def install_plugin(install_dir: str | None = None) -> str:
    install_dir = install_dir or default_install_dir()
    os.makedirs(install_dir, exist_ok=True)
    dest = os.path.join(install_dir, "agent.py")
    shutil.copy2(_plugin_source(), dest)
    return f"Installed callback plugin to {dest}"


def uninstall_plugin(install_dir: str | None = None) -> str:
    install_dir = install_dir or default_install_dir()
    dest = os.path.join(install_dir, "agent.py")
    if os.path.isfile(dest):
        os.remove(dest)
        return f"Removed {dest}"
    return f"Plugin not found at {dest}"
