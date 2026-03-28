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
    """Auto-configure detected agents. Returns list of detected agent modules."""
    if preselected is None:
        preselected = set()
    return list(preselected)
