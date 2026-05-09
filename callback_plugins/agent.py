"""Token-optimized stdout callback for AI agent consumption."""

from __future__ import annotations

DOCUMENTATION = """
    name: agent
    type: stdout
    short_description: Token-optimized output for AI agents
    version_added: "1.0"
    description:
        - Minimal, pipe-delimited output designed to reduce token usage
        - Only changed, failed, and unreachable results are shown
        - Skipped tasks and ok results are hidden entirely
        - Failures inline a single-line summary on the lead line and emit
          additional content as continuation lines prefixed with "msg> "
          or "stderr> " — stack traces and multi-line errors stay readable
        - rc is always emitted on failure when present, alongside any msg/stderr
        - RECAP line always shown with non-zero counts
        - HINT line is appended after RECAP when failures or unreachable hosts
          occurred and ANSIBLE_LOG_PATH is unset, pointing at the full-log
          escape hatch
"""

import difflib
import os

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
                diff_lines = list(
                    difflib.unified_diff(
                        str(before).splitlines(),
                        str(after).splitlines(),
                        lineterm="",
                    )
                )
                for line in diff_lines:
                    if line.startswith(("+", "-")) and not line.startswith(
                        ("+++", "---")
                    ):
                        return line
        elif isinstance(diff, list):
            for d in diff:
                summary = self._format_diff_summary(d)
                if summary:
                    return summary
        return None

    def _split_lines(self, text):
        """Strip and split text into a list of lines.

        Returns ``[]`` for empty/whitespace-only input. Trailing whitespace is
        stripped first so a single trailing newline doesn't produce a phantom
        continuation line. Inner whitespace is preserved so indented stack
        trace frames survive intact.
        """
        if not text:
            return []
        return str(text).strip().splitlines()

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

    def _emit_failure(self, lead_prefix, result):
        """Emit a failure block: lead line plus optional continuation lines.

        ``lead_prefix`` already contains everything up to (but not including)
        the first appended msg/stderr/rc field — e.g. ``failed | db01`` or
        ``failed | web01 | item: badpkg``.
        """
        msg_lines = self._split_lines(result.result.get("msg"))
        stderr_lines = self._split_lines(result.result.get("stderr"))
        rc = result.result.get("rc")

        parts = [lead_prefix]
        if msg_lines:
            parts.append(f"msg: {msg_lines[0]}")
        if stderr_lines:
            parts.append(f"stderr: {stderr_lines[0]}")
        if rc is not None:
            parts.append(f"rc: {rc}")

        if len(parts) == 1:
            parts.append("msg: (no details)")

        self._emit(" | ".join(parts))

        for line in msg_lines[1:]:
            self._emit(f"msg> {line}")
        for line in stderr_lines[1:]:
            self._emit(f"stderr> {line}")

    def v2_runner_on_failed(self, result, ignore_errors=False):
        self._flush_task_banner()
        host = result.host.get_name()
        self._emit_failure(f"failed | {host}", result)
        if ignore_errors:
            self._emit("...ignoring")

    def v2_runner_on_unreachable(self, result):
        self._flush_task_banner()
        host = result.host.get_name()
        msg_lines = self._split_lines(result.result.get("msg"))
        if not msg_lines:
            self._emit(f"unreachable | {host}")
            return
        self._emit(f"unreachable | {host} | {msg_lines[0]}")
        for line in msg_lines[1:]:
            self._emit(f"msg> {line}")

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
        self._emit_failure(f"failed | {host} | item: {item}", result)

    def v2_runner_item_on_skipped(self, result):
        pass

    def v2_playbook_on_stats(self, stats):
        hosts = sorted(stats.processed.keys())
        host_summaries = []
        has_problems = False
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
            if counts["failed"] or counts["unreachable"]:
                has_problems = True
            parts = [f"{k}={v}" for k, v in counts.items() if v > 0]
            if parts:
                host_summaries.append(f"{host}: {' '.join(parts)}")
            else:
                host_summaries.append(f"{host}: ok=0")

        self._emit("RECAP | " + " | ".join(host_summaries))

        # Surface the escape hatch only when the agent will actually need it:
        # something failed and the user hasn't already opted into full logging.
        # Empty string matches Ansible's own "logging disabled" semantics.
        if has_problems and not os.environ.get("ANSIBLE_LOG_PATH"):
            self._emit("HINT | set ANSIBLE_LOG_PATH=<path> and re-run for full output")
