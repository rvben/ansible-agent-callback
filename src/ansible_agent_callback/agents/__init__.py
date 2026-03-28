"""Agent registry and interactive selector."""

from __future__ import annotations

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
    """Interactive multi-select with arrow keys, space to toggle, enter to confirm."""
    if preselected is None:
        preselected = set()

    if not sys.stdin.isatty():
        return list(preselected)

    try:
        import termios
        import tty
    except ImportError:
        return list(preselected)

    selected = {i for i, a in enumerate(agents) if a in preselected}
    cursor = 0
    fd = sys.stdin.fileno()

    try:
        old_settings = termios.tcgetattr(fd)
    except termios.error:
        return list(preselected)

    lines_written = (
        len(agents) + 2
    )  # header + agents + blank (hint has no trailing newline)

    def draw(first=False):
        buf = ""
        if not first:
            buf += f"\r\033[{lines_written}A"
        buf += "\033[J"
        buf += "  Configure for AI agents:\r\n"
        for i, agent in enumerate(agents):
            check = "\033[32m✓\033[0m" if i in selected else " "
            detected = " \033[2m(detected)\033[0m" if agent.detect() else ""
            padded = f"{agent.NAME:<20s}"
            if i == cursor:
                padded = f"\033[1m{padded}\033[0m"
            arrow = "\033[36m❯\033[0m" if i == cursor else " "
            buf += f"  {arrow} [{check}] {padded} {agent.CONFIG_PATH}{detected}\r\n"
        buf += "\r\n"
        buf += "  \033[2m↑/↓ move  ␣ toggle  ⏎ confirm\033[0m"
        sys.stdout.write(buf)
        sys.stdout.flush()

    sys.stdout.write("\033[?25l")
    sys.stdout.flush()
    try:
        tty.setraw(fd)
        draw(first=True)

        while True:
            ch = sys.stdin.read(1)
            if ch in ("\r", "\n"):
                break
            elif ch == " ":
                selected.symmetric_difference_update({cursor})
                draw()
            elif ch == "\x1b":
                s = sys.stdin.read(2)
                if s == "[A" and cursor > 0:
                    cursor -= 1
                    draw()
                elif s == "[B" and cursor < len(agents) - 1:
                    cursor += 1
                    draw()
            elif ch == "\x03":
                raise KeyboardInterrupt
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        sys.stdout.write(f"\r\033[{lines_written}A\033[J")
        sys.stdout.write("  Configure for AI agents:\n")
        for i, agent in enumerate(agents):
            if i in selected:
                sys.stdout.write(
                    f"    \033[32m✓\033[0m {agent.NAME:<20s} {agent.CONFIG_PATH}\n"
                )
            else:
                sys.stdout.write(
                    f"    \033[2m-\033[0m \033[2m{agent.NAME:<20s} {agent.CONFIG_PATH}\033[0m\n"
                )
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()

    return [agents[i] for i in sorted(selected)]
