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
        - When ANSIBLE_LOG_PATH is set, full detail for failed/unreachable tasks is
          written to <ANSIBLE_LOG_PATH>.details.jsonl and a LOG line points to it
        - When ANSIBLE_LOG_PATH is unset, a HINT line after RECAP points at that
          escape hatch
"""

import difflib
import json
import os

from ansible import constants as C
from ansible.parsing.ajson import AnsibleJSONEncoder
from ansible.plugins.callback import CallbackBase


class CallbackModule(CallbackBase):
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = "stdout"
    CALLBACK_NAME = "agent"

    def __init__(self):
        super().__init__()
        self._pending_task = None
        self._current_task_name = None
        self._details_target = None
        self._details_cleared = False

    def _emit(self, line):
        self._display.display(line)

    def _flush_task_banner(self):
        if self._pending_task:
            self._emit(f"TASK | {self._pending_task}")
            self._pending_task = None

    def v2_playbook_on_start(self, playbook):
        # Clear a details file left by a previous invocation, so a run that
        # produces no failures leaves nothing at the deterministic companion
        # path. Multiple playbooks passed to one `ansible-playbook` call share
        # this callback instance and must accumulate into a single file, so only
        # the first playbook start clears it.
        if self._details_cleared:
            return
        self._details_cleared = True
        target = self._details_path()
        if not target:
            return
        try:
            os.remove(target)
        except OSError:
            pass

    def v2_playbook_on_play_start(self, play):
        name = play.get_name().strip()
        self._emit(f"PLAY | {name}")

    def v2_playbook_on_task_start(self, task, is_conditional):
        name = task.get_name().strip()
        self._pending_task = name
        self._current_task_name = name

    def v2_playbook_on_handler_task_start(self, task):
        name = task.get_name().strip()
        self._current_task_name = name
        self._emit(f"HANDLER | {name}")

    def _format_diff_summary(self, diff):
        """Pick a representative change line and append totals when relevant.

        Comment-only changes (lines starting with ``#`` or ``;`` after the
        diff marker) get skipped when picking the representative line so an
        agent doesn't draw conclusions from a comment removal while the real
        edit is buried below. If every change is a comment, the first comment
        change is shown as fallback.

        Totals ``(+N -M)`` are appended when the diff spans multiple changed
        lines on either side — they signal "there's more" without forcing the
        agent to read the full diff.
        """
        if not diff:
            return None
        if isinstance(diff, list):
            for d in diff:
                summary = self._format_diff_summary(d)
                if summary:
                    return summary
            return None
        if not isinstance(diff, dict):
            return None

        before = diff.get("before", "")
        after = diff.get("after", "")
        if not (before and after):
            return None

        plus = minus = 0
        first_change = None
        first_non_comment = None
        for line in difflib.unified_diff(
            str(before).splitlines(),
            str(after).splitlines(),
            lineterm="",
        ):
            if line.startswith(("+++", "---")):
                continue
            if line.startswith("+"):
                plus += 1
            elif line.startswith("-"):
                minus += 1
            else:
                continue
            if first_change is None:
                first_change = line
            if first_non_comment is None and not line[1:].lstrip().startswith(
                ("#", ";")
            ):
                first_non_comment = line

        representative = first_non_comment or first_change
        if representative is None:
            return None
        if plus > 1 or minus > 1:
            return f"{representative} (+{plus} -{minus})"
        return representative

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
        self._write_detail("ignored" if ignore_errors else "failed", result)

    def v2_runner_on_unreachable(self, result):
        self._flush_task_banner()
        host = result.host.get_name()
        msg_lines = self._split_lines(result.result.get("msg"))
        if not msg_lines:
            self._emit(f"unreachable | {host}")
        else:
            self._emit(f"unreachable | {host} | {msg_lines[0]}")
            for line in msg_lines[1:]:
                self._emit(f"msg> {line}")
        self._write_detail("unreachable", result)

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
        self._write_detail("failed", result, item=item)

    def v2_runner_item_on_skipped(self, result):
        pass

    def _log_path(self):
        """Resolve the configured Ansible log path, if any.

        Prefers the ANSIBLE_LOG_PATH environment variable (matching Ansible's
        own precedence) and falls back to the [defaults] log_path setting from
        ansible.cfg. Returns an absolute path, or None when file logging is not
        configured.
        """
        raw = os.environ.get("ANSIBLE_LOG_PATH") or getattr(C, "DEFAULT_LOG_PATH", None)
        if not raw:
            return None
        return os.path.abspath(os.path.expanduser(str(raw)))

    def _details_path(self):
        """Path to the companion file holding full detail for failures.

        The concise stdout is mirrored verbatim into ANSIBLE_LOG_PATH, so that
        log cannot recover the fields this callback trims. Instead the untrimmed
        results are written next to it, at <ANSIBLE_LOG_PATH>.details.jsonl.
        Returns None when no log path is configured.
        """
        log_path = self._log_path()
        if not log_path:
            return None
        return log_path + ".details.jsonl"

    def _write_detail(self, status, result, item=None):
        """Append one host's full, untrimmed result to the details file.

        Internal (_ansible_*) keys and the module invocation are dropped: the
        invocation echoes task arguments (a needless secret surface) and adds
        nothing to debugging beyond msg/stderr/stdout/rc. Results for no_log
        tasks are already censored by ansible-core before reaching callbacks.
        """
        target = self._details_path()
        if not target:
            return
        record = {
            "status": status,
            "host": result.host.get_name(),
            "task": self._current_task_name,
        }
        if item is not None:
            record["item"] = item
        record["result"] = {
            key: value
            for key, value in result.result.items()
            if not key.startswith("_ansible_") and key != "invocation"
        }
        line = json.dumps(record, cls=AnsibleJSONEncoder)
        # The first successful write truncates any file left by a previous run;
        # later writes this run append. A write failure (e.g. an unwritable
        # directory) must never abort the play, so it is swallowed and the LOG
        # pointer is simply not emitted.
        mode = "a" if self._details_target else "w"
        try:
            with open(target, mode, encoding="utf-8") as handle:
                handle.write(line + "\n")
        except OSError:
            return
        self._details_target = target

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

        # When detail was captured, point agents straight at it. Otherwise, if
        # something failed without a log path configured, surface the escape
        # hatch. Setting ANSIBLE_LOG_PATH captures the full result to a companion
        # file, so the hint promises exactly what re-running delivers.
        if self._details_target:
            self._emit(f"LOG | {self._details_target}")
        elif has_problems and not self._log_path():
            self._emit(
                "HINT | set ANSIBLE_LOG_PATH=<path> and re-run to capture full failure detail"
            )
