"""Token-optimized stdout callback for AI agent consumption."""

from __future__ import annotations

DOCUMENTATION = """
    name: agent
    type: stdout
    short_description: Token-optimized output for AI agents
    version_added: "1.0"
    description:
        - Minimal, pipe-delimited output designed to reduce token usage
        - One line per event, no color codes, no decorative banners
        - Only changed, failed, and unreachable results are shown
        - Skipped tasks and ok results are hidden entirely
        - RECAP line always shown with non-zero counts
"""

import difflib

from ansible.plugins.callback import CallbackBase


class CallbackModule(CallbackBase):
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = "stdout"
    CALLBACK_NAME = "agent"

    def __init__(self):
        super().__init__()
        self._pending_task = None

    def _emit(self, line):
        self._display.display(line)

    def _flush_task_banner(self):
        if self._pending_task:
            self._emit(f"TASK | {self._pending_task}")
            self._pending_task = None

    def v2_playbook_on_play_start(self, play):
        name = play.get_name().strip()
        self._emit(f"PLAY | {name}")

    def v2_playbook_on_task_start(self, task, is_conditional):
        self._pending_task = task.get_name().strip()

    def v2_playbook_on_handler_task_start(self, task):
        name = task.get_name().strip()
        self._emit(f"HANDLER | {name}")

    def _format_diff_summary(self, diff):
        """Extract first meaningful changed line from diff data."""
        if not diff:
            return None
        if isinstance(diff, dict):
            before = diff.get("before", "")
            after = diff.get("after", "")
            if before and after:
                diff_lines = list(difflib.unified_diff(
                    str(before).splitlines(),
                    str(after).splitlines(),
                    lineterm="",
                ))
                for line in diff_lines:
                    if line.startswith(("+", "-")) and not line.startswith(("+++", "---")):
                        return line
        elif isinstance(diff, list):
            for d in diff:
                summary = self._format_diff_summary(d)
                if summary:
                    return summary
        return None

    def _sanitize(self, text):
        """Replace newlines with literal \\n for single-line output."""
        if not text:
            return text
        return str(text).replace("\n", r"\n").replace("\r", r"\r")

    def v2_runner_on_ok(self, result):
        # Suppress post-loop aggregate line
        if "results" in result.result:
            return

        host = result.host.get_name()
        changed = result.result.get("changed", False)

        # Only show changed results — ok results are noise
        if not changed:
            return

        self._flush_task_banner()
        parts = [f"changed | {host}"]
        diff = result.result.get("diff")
        if diff:
            summary = self._format_diff_summary(diff)
            if summary:
                parts.append(f"diff: {summary}")
        self._emit(" | ".join(parts))

    def v2_runner_on_failed(self, result, ignore_errors=False):
        self._flush_task_banner()
        host = result.host.get_name()
        parts = [f"failed | {host}"]

        msg = result.result.get("msg")
        if msg:
            parts.append(f"msg: {self._sanitize(msg)}")

        stderr = result.result.get("stderr")
        if stderr:
            parts.append(f"stderr: {self._sanitize(stderr)}")

        rc = result.result.get("rc")
        if rc is not None and len(parts) == 1:
            parts.append(f"rc: {rc}")

        if len(parts) == 1:
            parts.append("msg: (no details)")

        self._emit(" | ".join(parts))

        if ignore_errors:
            self._emit("...ignoring")

    def v2_runner_on_unreachable(self, result):
        self._flush_task_banner()
        host = result.host.get_name()
        msg = self._sanitize(result.result.get("msg", ""))
        self._emit(f"unreachable | {host} | {msg}")

    def v2_runner_on_skipped(self, result):
        pass

    def _get_item_label(self, result_dict):
        """Get the item label from a result dict."""
        item = result_dict.get("item", "")
        return str(item)

    def v2_runner_item_on_ok(self, result):
        # Only show changed loop items
        changed = result.result.get("changed", False)
        if not changed:
            return

        self._flush_task_banner()
        host = result.host.get_name()
        item = self._get_item_label(result.result)
        self._emit(f"changed | {host} | item: {item}")

    def v2_runner_item_on_failed(self, result):
        self._flush_task_banner()
        host = result.host.get_name()
        item = self._get_item_label(result.result)
        parts = [f"failed | {host} | item: {item}"]

        msg = result.result.get("msg")
        if msg:
            parts.append(f"msg: {self._sanitize(msg)}")

        stderr = result.result.get("stderr")
        if stderr:
            parts.append(f"stderr: {self._sanitize(stderr)}")

        self._emit(" | ".join(parts))

    def v2_runner_item_on_skipped(self, result):
        pass

    def v2_playbook_on_stats(self, stats):
        hosts = sorted(stats.processed.keys())
        host_summaries = []
        for host in hosts:
            s = stats.summarize(host)
            counts = {
                "ok": s.get("ok", 0),
                "changed": s.get("changed", 0),
                "unreachable": s.get("unreachable", 0),
                "failed": s.get("failures", 0),
                "skipped": s.get("skipped", 0),
                "rescued": s.get("rescued", 0),
                "ignored": s.get("ignored", 0),
            }
            parts = [f"{k}={v}" for k, v in counts.items() if v > 0]
            if parts:
                host_summaries.append(f"{host}: {' '.join(parts)}")
            else:
                host_summaries.append(f"{host}: ok=0")

        self._emit("RECAP | " + " | ".join(host_summaries))
