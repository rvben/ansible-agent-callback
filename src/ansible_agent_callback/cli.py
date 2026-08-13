"""CLI entry point for ansible-agent-callback."""

from __future__ import annotations

import argparse
import json
import sys
from importlib.metadata import PackageNotFoundError, version

from ansible_agent_callback import installer
from ansible_agent_callback.agents import (
    detected_agents,
    get_agent_by_slug,
    get_all_agents,
    select_agents_interactive,
)


class CliArgumentParser(argparse.ArgumentParser):
    """Argument parser whose failures end with a machine-readable envelope."""

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        print(
            json.dumps({"error": {"kind": "invalid_usage", "message": message}}),
            file=sys.stderr,
        )
        self.exit(2)


def _version() -> str:
    try:
        return version("ansible-agent-callback")
    except PackageNotFoundError:
        return "0.3.1"


def _output_mode(requested: str) -> str:
    if requested == "auto":
        return "text" if sys.stdout.isatty() else "json"
    return requested


def _emit(value: dict, text: list[str], output: str) -> None:
    if output == "json":
        print(json.dumps(value, indent=2, sort_keys=True))
    else:
        for line in text:
            print(line)


def cmd_install(args: list[str], install_dir: str | None = None, output: str = "text"):
    parser = CliArgumentParser(prog="ansible-agent-callback install")
    parser.add_argument(
        "--agents",
        type=str,
        default=None,
        help="Comma-separated agent slugs to configure",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        dest="all_agents",
        help="Configure all detected agents without prompting",
    )
    parser.add_argument(
        "--plugin-only",
        action="store_true",
        help="Only install plugin, skip agent configuration",
    )
    parsed = parser.parse_args(args)

    plugin_result = installer.install_plugin(install_dir)
    messages = [plugin_result]
    configured_agents: list[str] = []

    if parsed.plugin_only:
        _emit(
            {"installed": True, "plugin": plugin_result, "configured_agents": []},
            messages,
            output,
        )
        return

    all_agents = get_all_agents()

    if parsed.agents:
        slugs = [s.strip() for s in parsed.agents.split(",")]
        selected = [a for s in slugs if (a := get_agent_by_slug(s))]
        if not selected:
            message = f"No matching agents found for: {parsed.agents}"
            _emit(
                {"installed": True, "plugin": plugin_result, "configured_agents": []},
                [*messages, message],
                output,
            )
            return
    elif parsed.all_agents:
        selected = detected_agents()
    else:
        detected = set(detected_agents())
        selected = select_agents_interactive(all_agents, preselected=detected)

    if not selected:
        _emit(
            {"installed": True, "plugin": plugin_result, "configured_agents": []},
            messages,
            output,
        )
        return

    for agent in selected:
        result = agent.configure()
        configured_agents.append(agent.SLUG)
        messages.append(f"  \u2713 {result}")
    _emit(
        {
            "installed": True,
            "plugin": plugin_result,
            "configured_agents": configured_agents,
        },
        [messages[0], "", *messages[1:]],
        output,
    )


def cmd_uninstall(
    args: list[str], install_dir: str | None = None, output: str = "text"
):
    parser = CliArgumentParser(prog="ansible-agent-callback uninstall")
    parser.parse_args(args)

    all_agents = get_all_agents()
    configured = [a for a in all_agents if a.is_configured()]

    messages = []
    unconfigured_agents = []
    for agent in configured:
        result = agent.unconfigure()
        unconfigured_agents.append(agent.SLUG)
        messages.append(f"  \u2713 {result}")

    plugin_result = installer.uninstall_plugin(install_dir)
    messages.append(plugin_result)
    _emit(
        {
            "uninstalled": True,
            "plugin": plugin_result,
            "unconfigured_agents": unconfigured_agents,
        },
        messages,
        output,
    )


def cmd_update(args: list[str], install_dir: str | None = None, output: str = "text"):
    parser = CliArgumentParser(prog="ansible-agent-callback update")
    parser.parse_args(args)
    result = installer.install_plugin(install_dir)
    _emit({"updated": True, "plugin": result}, [result], output)


def cmd_env(args: list[str], output: str = "text"):
    parser = CliArgumentParser(prog="ansible-agent-callback env")
    parser.parse_args(args)
    export = "export ANSIBLE_STDOUT_CALLBACK=agent"
    _emit({"export": export}, [export], output)


def schema_document() -> dict:
    return {
        "$schema": "https://clispec.dev/schema/v0.3.json",
        "clispec": "0.3",
        "name": "ansible-agent-callback",
        "version": _version(),
        "description": "Token-optimized Ansible output for AI coding agents",
        "global_args": [
            {
                "name": "--output",
                "short": "-o",
                "type": "string",
                "default": "auto",
                "enum": ["auto", "text", "json"],
                "description": "Output format; auto uses text on a TTY and JSON when piped",
            }
        ],
        "output": {"tty": "text", "piped": "json"},
        "errors": [
            {
                "kind": "invalid_usage",
                "exit_code": 2,
                "retryable": False,
                "description": "Invalid command or argument",
            },
            {
                "kind": "error",
                "exit_code": 1,
                "retryable": False,
                "description": "Installation or configuration failed",
            },
        ],
        "commands": [
            {
                "name": "install",
                "description": "Install plugin and configure agents",
                "mutating": True,
                "effects": "idempotent",
                "cardinality": "single",
                "args": [
                    {"name": "--agents", "type": "string", "required": False},
                    {"name": "--all", "type": "boolean", "required": False},
                    {"name": "--plugin-only", "type": "boolean", "required": False},
                ],
                "output_fields": [
                    {"name": "installed", "type": "boolean"},
                    {"name": "plugin", "type": "string"},
                    {
                        "name": "configured_agents",
                        "type": "array",
                        "items": {"type": "string"},
                    },
                ],
            },
            {
                "name": "update",
                "description": "Update the installed plugin",
                "mutating": True,
                "effects": "idempotent",
                "cardinality": "single",
                "args": [],
                "output_fields": [
                    {"name": "updated", "type": "boolean"},
                    {"name": "plugin", "type": "string"},
                ],
            },
            {
                "name": "uninstall",
                "description": "Remove plugin and agent configuration",
                "mutating": True,
                "effects": "idempotent",
                "cardinality": "single",
                "args": [],
                "output_fields": [
                    {"name": "uninstalled", "type": "boolean"},
                    {"name": "plugin", "type": "string"},
                    {
                        "name": "unconfigured_agents",
                        "type": "array",
                        "items": {"type": "string"},
                    },
                ],
            },
            {
                "name": "env",
                "description": "Print the callback environment export",
                "mutating": False,
                "effects": "read_only",
                "cardinality": "single",
                "args": [],
                "output_fields": [{"name": "export", "type": "string"}],
            },
            {
                "name": "schema",
                "description": "Emit the machine-readable CLI contract",
                "mutating": False,
                "effects": "read_only",
                "cardinality": "single",
                "args": [],
                "stdout_schema": {"$ref": "https://clispec.dev/schema/v0.3.json"},
            },
            {
                "name": "capabilities",
                "description": "Describe offline-safe CLI capabilities",
                "mutating": False,
                "effects": "read_only",
                "cardinality": "single",
                "args": [],
                "example": {"args": ["capabilities"]},
                "output_fields": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "clispec", "type": "string"},
                    {
                        "name": "output",
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    {
                        "name": "features",
                        "type": "array",
                        "items": {"type": "string"},
                    },
                ],
            },
            {
                "name": "completions",
                "description": "Generate a shell completion script",
                "mutating": False,
                "effects": "read_only",
                "output_kind": "opaque",
                "media_type": "text/plain",
                "args": [
                    {
                        "name": "shell",
                        "type": "string",
                        "required": True,
                        "enum": ["bash", "zsh", "fish"],
                    }
                ],
            },
        ],
    }


def cmd_schema(args: list[str]):
    parser = CliArgumentParser(prog="ansible-agent-callback schema")
    parser.parse_args(args)
    print(json.dumps(schema_document(), indent=2, sort_keys=True))


def cmd_capabilities(args: list[str], output: str = "text"):
    parser = CliArgumentParser(prog="ansible-agent-callback capabilities")
    parser.parse_args(args)
    value = {
        "name": "ansible-agent-callback",
        "version": _version(),
        "clispec": "0.3",
        "output": ["text", "json"],
        "features": ["schema", "structured output", "shell completions"],
    }
    _emit(
        value,
        [
            (
                f"ansible-agent-callback {_version()} - clispec 0.3; "
                "text/json output, schema, shell completions"
            )
        ],
        output,
    )


def cmd_completions(args: list[str]):
    parser = CliArgumentParser(prog="ansible-agent-callback completions")
    parser.add_argument("shell", choices=["bash", "zsh", "fish"])
    shell = parser.parse_args(args).shell
    commands = "install update uninstall env schema capabilities completions"
    if shell == "bash":
        print(f"complete -W '{commands}' ansible-agent-callback")
    elif shell == "zsh":
        print(f"compdef '_arguments 1:command:({commands})' ansible-agent-callback")
    else:
        print(f"complete -c ansible-agent-callback -f -a '{commands}'")


def _normalize_global_output(argv: list[str]) -> list[str]:
    """Permit the global output flag before or after a subcommand."""
    normalized = list(argv)
    for index, value in enumerate(normalized):
        if value.startswith("--output="):
            return [normalized.pop(index), *normalized]
        if value in {"--output", "-o"} and index + 1 < len(normalized):
            flag, selected = normalized[index : index + 2]
            del normalized[index : index + 2]
            return [flag, selected, *normalized]
    return normalized


def main():
    parser = CliArgumentParser(
        prog="ansible-agent-callback",
        description="Token-optimized Ansible output for AI coding agents",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {_version()}")
    parser.add_argument(
        "--output",
        "-o",
        choices=["auto", "text", "json"],
        default="auto",
        help="Output format (default: auto)",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("install", help="Install plugin and configure agents")
    subparsers.add_parser("update", help="Update the plugin to the latest version")
    subparsers.add_parser("uninstall", help="Remove plugin and agent configuration")
    subparsers.add_parser("env", help="Print environment variable export")
    subparsers.add_parser("schema", help="Emit the machine-readable CLI contract")
    subparsers.add_parser("capabilities", help="Describe offline-safe capabilities")
    subparsers.add_parser("completions", help="Generate shell completions")

    parsed, remaining = parser.parse_known_args(_normalize_global_output(sys.argv[1:]))

    output = _output_mode(parsed.output)
    if parsed.command == "install":
        cmd_install(remaining, output=output)
    elif parsed.command == "update":
        cmd_update(remaining, output=output)
    elif parsed.command == "uninstall":
        cmd_uninstall(remaining, output=output)
    elif parsed.command == "env":
        cmd_env(remaining, output=output)
    elif parsed.command == "schema":
        cmd_schema(remaining)
    elif parsed.command == "capabilities":
        cmd_capabilities(remaining, output=output)
    elif parsed.command == "completions":
        cmd_completions(remaining)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
