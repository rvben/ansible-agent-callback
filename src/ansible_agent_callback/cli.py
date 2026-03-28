"""CLI entry point for ansible-agent-callback."""

from __future__ import annotations

import argparse
import sys

from ansible_agent_callback import installer
from ansible_agent_callback.agents import (
    get_all_agents,
    get_agent_by_slug,
    detected_agents,
    select_agents_interactive,
)


def cmd_install(args: list[str], install_dir: str | None = None):
    parser = argparse.ArgumentParser(prog="ansible-agent-callback install")
    parser.add_argument("--agents", type=str, default=None,
                        help="Comma-separated agent slugs to configure")
    parser.add_argument("--all", action="store_true", dest="all_agents",
                        help="Configure all detected agents without prompting")
    parser.add_argument("--plugin-only", action="store_true",
                        help="Only install plugin, skip agent configuration")
    parsed = parser.parse_args(args)

    result = installer.install_plugin(install_dir)
    print(result)

    if parsed.plugin_only:
        return

    all_agents = get_all_agents()

    if parsed.agents:
        slugs = [s.strip() for s in parsed.agents.split(",")]
        selected = [a for s in slugs if (a := get_agent_by_slug(s))]
        if not selected:
            print(f"No matching agents found for: {parsed.agents}")
            return
    elif parsed.all_agents:
        selected = detected_agents()
    else:
        detected = set(detected_agents())
        selected = select_agents_interactive(all_agents, preselected=detected)

    if not selected:
        return

    print()
    for agent in selected:
        result = agent.configure()
        print(f"  \u2713 {result}")


def cmd_uninstall(args: list[str], install_dir: str | None = None):
    parser = argparse.ArgumentParser(prog="ansible-agent-callback uninstall")
    parsed = parser.parse_args(args)

    all_agents = get_all_agents()
    configured = [a for a in all_agents if a.is_configured()]

    for agent in configured:
        result = agent.unconfigure()
        print(f"  \u2713 {result}")

    result = installer.uninstall_plugin(install_dir)
    print(result)


def cmd_update(args: list[str], install_dir: str | None = None):
    result = installer.install_plugin(install_dir)
    print(result)


def cmd_env(args: list[str]):
    print("export ANSIBLE_STDOUT_CALLBACK=agent")


def main():
    parser = argparse.ArgumentParser(
        prog="ansible-agent-callback",
        description="Token-optimized Ansible output for AI coding agents",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("install", help="Install plugin and configure agents")
    subparsers.add_parser("update", help="Update the plugin to the latest version")
    subparsers.add_parser("uninstall", help="Remove plugin and agent configuration")
    subparsers.add_parser("env", help="Print environment variable export")

    parsed, remaining = parser.parse_known_args()

    if parsed.command == "install":
        cmd_install(remaining)
    elif parsed.command == "update":
        cmd_update(remaining)
    elif parsed.command == "uninstall":
        cmd_uninstall(remaining)
    elif parsed.command == "env":
        cmd_env(remaining)
    else:
        parser.print_help()
        sys.exit(1)
