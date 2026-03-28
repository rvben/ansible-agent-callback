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
    cursor = 0
    total_lines = len(agents) + 2  # header + agents + footer

    try:
        import termios
        import tty

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
    except (ImportError, termios.error, ValueError):
        return _select_numbered_fallback(agents, preselected)

    def render(first=False):
        if not first:
            # Move cursor to top of our output area
            sys.stdout.write(f"\033[{total_lines}A")
        # Clear from cursor to end of screen
        sys.stdout.write("\033[J")
        sys.stdout.write("Configure for AI agents:\r\n")
        for i, agent in enumerate(agents):
            check = "x" if i in selected else " "
            prefix = ">" if i == cursor else " "
            detected = " [detected]" if agent.detect() else ""
            sys.stdout.write(
                f"  {prefix} [{check}] {agent.NAME:<20s} ({agent.CONFIG_PATH}){detected}\r\n"
            )
        sys.stdout.write("\u2191\u2193 navigate  \u2423 toggle  \u23ce confirm")
        sys.stdout.flush()

    try:
        tty.setraw(fd)
        render(first=True)

        while True:
            ch = sys.stdin.read(1)
            if ch == "\r" or ch == "\n":
                break
            elif ch == " ":
                if cursor in selected:
                    selected.discard(cursor)
                else:
                    selected.add(cursor)
                render()
            elif ch == "\x1b":
                seq = sys.stdin.read(2)
                if seq == "[A" and cursor > 0:
                    cursor -= 1
                    render()
                elif seq == "[B" and cursor < len(agents) - 1:
                    cursor += 1
                    render()
            elif ch == "\x03":
                raise KeyboardInterrupt
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        sys.stdout.write("\r\n\r\n")
        sys.stdout.flush()

    return [agents[i] for i in sorted(selected)]


def _select_numbered_fallback(agents, preselected):
    """Fallback for non-interactive terminals."""
    print("Configure for AI agents:")
    for i, agent in enumerate(agents):
        detected = " [detected]" if agent.detect() else ""
        pre = "*" if agent in preselected else " "
        print(f"  {pre} {i + 1}. {agent.NAME:<20s} ({agent.CONFIG_PATH}){detected}")
    print()
    print("Enter numbers to toggle (comma-separated), or press Enter for detected agents:")
    line = input("> ").strip()
    if not line:
        return list(preselected)
    indices = {int(x.strip()) - 1 for x in line.split(",") if x.strip().isdigit()}
    return [agents[i] for i in sorted(indices) if 0 <= i < len(agents)]
