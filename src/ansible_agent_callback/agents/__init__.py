"""Agent registry and interactive selector."""

from __future__ import annotations

import os
import sys

ALL_AGENTS: list = []


def _load_agents():
    if ALL_AGENTS:
        return
    from ansible_agent_callback.agents import (
        ansible_cfg,
        claude_code,
        codex_cli,
        gemini_cli,
        shell,
    )
    ALL_AGENTS.extend([claude_code, codex_cli, gemini_cli, shell, ansible_cfg])


def get_all_agents():
    _load_agents()
    return ALL_AGENTS


def get_agent_by_slug(slug: str):
    for agent in get_all_agents():
        if agent.SLUG == slug:
            return agent
    return None


def detected_agents():
    return [a for a in get_all_agents() if a.detect()]


def select_agents_interactive(agents, preselected=None):
    """Interactive multi-select. Returns list of selected agent modules."""
    if preselected is None:
        preselected = set()

    if not sys.stdin.isatty():
        return list(preselected)

    selected = {i for i, a in enumerate(agents) if a in preselected}

    print("Configure for AI agents:")
    for i, agent in enumerate(agents):
        check = "x" if i in selected else " "
        detected = " [detected]" if agent.detect() else ""
        print(f"  [{check}] {i + 1}. {agent.NAME:<20s} ({agent.CONFIG_PATH}){detected}")
    print()
    print("Enter numbers to toggle (comma-separated), or press Enter to accept:")
    try:
        line = input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return []

    if not line:
        return [agents[i] for i in sorted(selected)]

    # Toggle the specified indices
    for token in line.split(","):
        token = token.strip()
        if token.isdigit():
            idx = int(token) - 1
            if 0 <= idx < len(agents):
                if idx in selected:
                    selected.discard(idx)
                else:
                    selected.add(idx)

    return [agents[i] for i in sorted(selected)]
