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
        - Skipped tasks are hidden entirely
        - Full details only on failures
"""

from ansible.plugins.callback import CallbackBase


class CallbackModule(CallbackBase):
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = "stdout"
    CALLBACK_NAME = "agent"

    def _emit(self, line):
        self._display.display(line)

    def v2_playbook_on_play_start(self, play):
        name = play.get_name().strip()
        self._emit(f"PLAY | {name}")

    def v2_playbook_on_task_start(self, task, is_conditional):
        name = task.get_name().strip()
        self._emit(f"TASK | {name}")

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
                import difflib
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
        host = result.host.get_name()
        changed = result.result.get("changed", False)

        if changed:
            parts = [f"changed | {host}"]
            diff = result.result.get("diff")
            if diff:
                summary = self._format_diff_summary(diff)
                if summary:
                    parts.append(f"diff: {summary}")
            self._emit(" | ".join(parts))
        else:
            self._emit(f"ok | {host}")

    def v2_runner_on_failed(self, result, ignore_errors=False):
        host = result.host.get_name()
        parts = [f"failed | {host}"]

        msg = result.result.get("msg")
        if msg:
            parts.append(f"msg: {self._sanitize(msg)}")

        stderr = result.result.get("stderr")
        if stderr:
            parts.append(f"stderr: {self._sanitize(stderr)}")

        if len(parts) == 1:
            parts.append("msg: (no details)")

        self._emit(" | ".join(parts))

        if ignore_errors:
            self._emit("...ignoring")

    def v2_runner_on_unreachable(self, result):
        host = result.host.get_name()
        msg = self._sanitize(result.result.get("msg", ""))
        self._emit(f"unreachable | {host} | {msg}")

    def v2_runner_on_skipped(self, result):
        pass  # Hidden entirely per spec

    def _get_item_label(self, result_dict):
        """Get the item label from a result dict."""
        item = result_dict.get("item", "")
        return str(item)

    def v2_runner_item_on_ok(self, result):
        host = result.host.get_name()
        item = self._get_item_label(result.result)
        changed = result.result.get("changed", False)
        status = "changed" if changed else "ok"
        self._emit(f"{status} | {host} | item: {item}")

    def v2_runner_item_on_failed(self, result):
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
        pass  # Hidden entirely per spec

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
