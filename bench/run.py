"""Compare default vs agent stdout callback output volume.

Runs the same fixture playbook twice and reports byte/line/word counts
plus reduction percentages. Output is markdown so it can be pasted into
the README or CI logs verbatim.

Usage:
    python bench/run.py            # human-readable comparison
    python bench/run.py --json     # machine-readable summary
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLAYBOOK = ROOT / "bench" / "playbook.yml"
INVENTORY = ROOT / "bench" / "inventory.ini"
PLUGIN_DIR = ROOT / "callback_plugins"

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def run_playbook(callback: str) -> str:
    """Run the fixture playbook with the given stdout callback."""
    env = os.environ.copy()
    env["ANSIBLE_STDOUT_CALLBACK"] = callback
    env["ANSIBLE_CALLBACK_PLUGINS"] = str(PLUGIN_DIR)
    env["ANSIBLE_LOAD_CALLBACK_PLUGINS"] = "True"
    env["ANSIBLE_NOCOLOR"] = "True"
    env["ANSIBLE_FORCE_COLOR"] = "False"
    # HINT line should appear for the agent callback in the failure scenario,
    # which is part of what we measure — don't let an ambient log path hide it.
    env.pop("ANSIBLE_LOG_PATH", None)

    result = subprocess.run(
        ["ansible-playbook", "-i", str(INVENTORY), str(PLAYBOOK)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return ANSI_RE.sub("", result.stdout)


def metrics(text: str) -> dict[str, int]:
    return {
        "bytes": len(text.encode("utf-8")),
        "lines": len(text.splitlines()),
        "words": len(text.split()),
    }


def reduction(default: int, agent: int) -> float:
    if default == 0:
        return 0.0
    return (1 - agent / default) * 100


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON summary")
    parser.add_argument(
        "--show-output",
        action="store_true",
        help="include both raw outputs in the markdown report",
    )
    args = parser.parse_args()

    default_out = run_playbook("default")
    agent_out = run_playbook("agent")

    d = metrics(default_out)
    a = metrics(agent_out)
    summary = {
        "default": d,
        "agent": a,
        "reduction_pct": {key: round(reduction(d[key], a[key]), 1) for key in d},
    }

    if args.json:
        print(json.dumps(summary, indent=2))
        return 0

    print("# ansible-agent-callback: output volume comparison\n")
    print(f"Fixture: `{PLAYBOOK.relative_to(ROOT)}`")
    print(f"Inventory: `{INVENTORY.relative_to(ROOT)}` (localhost only)\n")
    print("| Metric | default | agent | Reduction |")
    print("|--------|---------|-------|-----------|")
    for key in ("bytes", "lines", "words"):
        print(
            f"| {key} | {d[key]:,} | {a[key]:,} | "
            f"{summary['reduction_pct'][key]:.1f}% |"
        )

    if args.show_output:
        print("\n---\n")
        print("## Default callback output\n")
        print("```text")
        print(default_out.rstrip())
        print("```\n")
        print("## Agent callback output\n")
        print("```text")
        print(agent_out.rstrip())
        print("```")
    return 0


if __name__ == "__main__":
    sys.exit(main())
