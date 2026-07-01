"""Tests for the agent callback plugin."""

import json
import sys
import os
from unittest.mock import MagicMock

import pytest

# Support both callback_plugins (local dev) and src layout
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "callback_plugins"))
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "src", "ansible_agent_callback")
)

try:
    import agent as _module
except ImportError:
    import plugin as _module


@pytest.fixture(autouse=True)
def _no_ansible_log(monkeypatch):
    """Keep tests hermetic: no log path is configured unless a test sets one.

    Without this, an ambient ANSIBLE_LOG_PATH or an ansible.cfg log_path would
    change the HINT/LOG branch and trigger details-file writes.
    """
    monkeypatch.delenv("ANSIBLE_LOG_PATH", raising=False)
    monkeypatch.setattr(_module.C, "DEFAULT_LOG_PATH", None, raising=False)


def make_plugin():
    """Create a plugin instance with captured output."""
    plugin = _module.CallbackModule()
    plugin._display = MagicMock()
    return plugin


def displayed_text(plugin):
    """Extract all displayed text from mock calls."""
    return [call.args[0] for call in plugin._display.display.call_args_list]


def make_play(name="Test Play"):
    """Create a mock play."""
    play = MagicMock()
    play.get_name.return_value = name
    return play


def make_task(name="Test Task", action="apt", uuid="task-1"):
    """Create a mock task."""
    task = MagicMock()
    task.get_name.return_value = f"  {name}  "
    task._uuid = uuid
    task.action = action
    task.loop = None
    task.no_log = False
    task.check_mode = False
    return task


def make_result(
    host="web01",
    task_name="Test Task",
    task_action="apt",
    task_uuid="task-1",
    changed=False,
    failed=False,
    msg="",
    stderr="",
    diff=None,
    loop=None,
    results=None,
):
    """Create a mock CallbackTaskResult."""
    result = MagicMock()
    result.host.get_name.return_value = host
    result.task = make_task(name=task_name, action=task_action, uuid=task_uuid)
    result.task.loop = loop
    result.result = {
        "changed": changed,
    }
    if msg:
        result.result["msg"] = msg
    if stderr:
        result.result["stderr"] = stderr
    if diff is not None:
        result.result["diff"] = diff
    if results is not None:
        result.result["results"] = results
    return result


class TestPlayBanner:
    def test_play_start_emits_play_line(self):
        plugin = make_plugin()
        play = make_play("Configure webservers")
        plugin.v2_playbook_on_play_start(play)
        assert displayed_text(plugin) == ["PLAY | Configure webservers"]

    def test_play_start_strips_whitespace(self):
        plugin = make_plugin()
        play = make_play("  My Play  ")
        plugin.v2_playbook_on_play_start(play)
        assert displayed_text(plugin) == ["PLAY | My Play"]


class TestDeferredTaskBanner:
    def test_task_start_alone_emits_nothing(self):
        plugin = make_plugin()
        task = make_task("Install nginx")
        plugin.v2_playbook_on_task_start(task, is_conditional=False)
        assert displayed_text(plugin) == []

    def test_task_banner_emitted_on_changed(self):
        plugin = make_plugin()
        task = make_task("Install nginx")
        plugin.v2_playbook_on_task_start(task, is_conditional=False)
        result = make_result(host="web01", changed=True)
        plugin.v2_runner_on_ok(result)
        assert displayed_text(plugin) == [
            "TASK | Install nginx",
            "changed | web01",
        ]

    def test_task_banner_emitted_on_failed(self):
        plugin = make_plugin()
        task = make_task("Install nginx")
        plugin.v2_playbook_on_task_start(task, is_conditional=False)
        result = make_result(host="web01", msg="broken")
        plugin.v2_runner_on_failed(result, ignore_errors=False)
        assert displayed_text(plugin) == [
            "TASK | Install nginx",
            "failed | web01 | msg: broken",
        ]

    def test_task_banner_emitted_on_unreachable(self):
        plugin = make_plugin()
        task = make_task("Install nginx")
        plugin.v2_playbook_on_task_start(task, is_conditional=False)
        result = make_result(host="web01", msg="timeout")
        plugin.v2_runner_on_unreachable(result)
        assert displayed_text(plugin) == [
            "TASK | Install nginx",
            "unreachable | web01 | timeout",
        ]

    def test_task_banner_not_emitted_when_all_ok(self):
        plugin = make_plugin()
        task = make_task("Install nginx")
        plugin.v2_playbook_on_task_start(task, is_conditional=False)
        result = make_result(host="web01", changed=False)
        plugin.v2_runner_on_ok(result)
        assert displayed_text(plugin) == []

    def test_task_banner_not_emitted_when_all_skipped(self):
        plugin = make_plugin()
        task = make_task("Conditional task")
        plugin.v2_playbook_on_task_start(task, is_conditional=False)
        result = make_result(host="web01")
        plugin.v2_runner_on_skipped(result)
        assert displayed_text(plugin) == []

    def test_banner_emitted_once_for_multiple_results(self):
        plugin = make_plugin()
        task = make_task("Configure nginx")
        plugin.v2_playbook_on_task_start(task, is_conditional=False)
        r1 = make_result(host="web01", changed=True)
        r2 = make_result(host="web02", changed=True)
        plugin.v2_runner_on_ok(r1)
        plugin.v2_runner_on_ok(r2)
        lines = displayed_text(plugin)
        assert lines.count("TASK | Configure nginx") == 1


class TestHandlerBanner:
    def test_handler_start_emits_handler_line(self):
        plugin = make_plugin()
        task = make_task("Restart nginx")
        plugin.v2_playbook_on_handler_task_start(task)
        assert displayed_text(plugin) == ["HANDLER | Restart nginx"]


class TestRunnerOk:
    def test_ok_unchanged_emits_nothing(self):
        plugin = make_plugin()
        result = make_result(host="web01")
        plugin.v2_runner_on_ok(result)
        assert displayed_text(plugin) == []

    def test_ok_changed(self):
        plugin = make_plugin()
        result = make_result(host="web01", changed=True)
        plugin.v2_runner_on_ok(result)
        assert "changed | web01" in displayed_text(plugin)

    def test_ok_changed_with_diff_single_line(self):
        # Single-line replace: no totals, the change is self-explanatory.
        plugin = make_plugin()
        diff = {"before": "workers 2\n", "after": "workers 4\n"}
        result = make_result(host="web01", changed=True, diff=diff)
        plugin.v2_runner_on_ok(result)
        assert "changed | web01 | diff: -workers 2" in displayed_text(plugin)

    def test_ok_changed_with_diff_multiline_appends_totals(self):
        # Multi-line change: include (+N -M) so the agent knows there's more
        # context than the single representative line.
        plugin = make_plugin()
        diff = {
            "before": "a\nb\nc\n",
            "after": "a\nB\nC\nD\n",
        }
        result = make_result(host="web01", changed=True, diff=diff)
        plugin.v2_runner_on_ok(result)
        lines = displayed_text(plugin)
        assert any(
            "changed | web01 | diff:" in line and "(+3 -2)" in line for line in lines
        )

    def test_ok_changed_with_diff_skips_comment_changes(self):
        # First non-comment change wins — `# old` removal is misleading when
        # the real edit is a config value change buried below.
        plugin = make_plugin()
        diff = {
            "before": "# old comment\nworkers 2\n",
            "after": "workers 4\n",
        }
        result = make_result(host="web01", changed=True, diff=diff)
        plugin.v2_runner_on_ok(result)
        lines = displayed_text(plugin)
        assert any("diff: -workers 2" in line for line in lines)
        assert not any("diff: -# old comment" in line for line in lines)

    def test_ok_changed_with_diff_falls_back_when_only_comments_change(self):
        # If every change is a comment, the comment is what changed — show it.
        plugin = make_plugin()
        diff = {
            "before": "# old comment\nworkers 4\n",
            "after": "# new comment\nworkers 4\n",
        }
        result = make_result(host="web01", changed=True, diff=diff)
        plugin.v2_runner_on_ok(result)
        lines = displayed_text(plugin)
        assert any("diff: -# old comment" in line for line in lines)

    def test_ok_changed_with_diff_skips_ini_style_comments(self):
        # INI/conf files use ; for comments — same heuristic should apply.
        plugin = make_plugin()
        diff = {
            "before": "; legacy note\nport=80\n",
            "after": "port=443\n",
        }
        result = make_result(host="web01", changed=True, diff=diff)
        plugin.v2_runner_on_ok(result)
        lines = displayed_text(plugin)
        assert any("diff: -port=80" in line for line in lines)

    def test_post_loop_aggregate_suppressed(self):
        plugin = make_plugin()
        result = make_result(host="web01", changed=False)
        result.result["results"] = [{"item": "nginx", "changed": False}]
        plugin.v2_runner_on_ok(result)
        assert displayed_text(plugin) == []

    def test_post_loop_aggregate_suppressed_even_when_changed(self):
        plugin = make_plugin()
        result = make_result(host="web01", changed=True)
        result.result["results"] = [{"item": "nginx", "changed": True}]
        plugin.v2_runner_on_ok(result)
        assert displayed_text(plugin) == []


class TestRunnerFailed:
    def test_failed_with_msg(self):
        plugin = make_plugin()
        result = make_result(host="db01", msg="unit not found")
        plugin.v2_runner_on_failed(result, ignore_errors=False)
        assert "failed | db01 | msg: unit not found" in displayed_text(plugin)

    def test_failed_with_stderr(self):
        plugin = make_plugin()
        result = make_result(host="db01", stderr="connection refused")
        plugin.v2_runner_on_failed(result, ignore_errors=False)
        assert "failed | db01 | stderr: connection refused" in displayed_text(plugin)

    def test_failed_with_msg_and_stderr(self):
        plugin = make_plugin()
        result = make_result(host="db01", msg="failed", stderr="err detail")
        plugin.v2_runner_on_failed(result, ignore_errors=False)
        assert "failed | db01 | msg: failed | stderr: err detail" in displayed_text(
            plugin
        )

    def test_failed_multiline_msg_emits_continuation(self):
        plugin = make_plugin()
        result = make_result(host="db01", msg="line1\nline2\nline3")
        plugin.v2_runner_on_failed(result, ignore_errors=False)
        assert displayed_text(plugin) == [
            "failed | db01 | msg: line1",
            "msg> line2",
            "msg> line3",
        ]

    def test_failed_multiline_stderr_emits_continuation(self):
        plugin = make_plugin()
        result = make_result(host="db01", msg="failed", stderr="err1\nerr2\nerr3")
        plugin.v2_runner_on_failed(result, ignore_errors=False)
        assert displayed_text(plugin) == [
            "failed | db01 | msg: failed | stderr: err1",
            "stderr> err2",
            "stderr> err3",
        ]

    def test_failed_both_multiline_msg_continuations_before_stderr(self):
        plugin = make_plugin()
        result = make_result(host="db01", msg="m1\nm2", stderr="s1\ns2\ns3")
        plugin.v2_runner_on_failed(result, ignore_errors=False)
        assert displayed_text(plugin) == [
            "failed | db01 | msg: m1 | stderr: s1",
            "msg> m2",
            "stderr> s2",
            "stderr> s3",
        ]

    def test_failed_multiline_preserves_indented_lines(self):
        # Stack traces rely on leading whitespace surviving the continuation prefix.
        traceback = (
            "Traceback (most recent call last):\n"
            '  File "/x", line 5, in <module>\n'
            "    do_thing()\n"
            "RuntimeError: oops"
        )
        plugin = make_plugin()
        result = make_result(host="db01", stderr=traceback)
        plugin.v2_runner_on_failed(result, ignore_errors=False)
        assert displayed_text(plugin) == [
            "failed | db01 | stderr: Traceback (most recent call last):",
            'stderr>   File "/x", line 5, in <module>',
            "stderr>     do_thing()",
            "stderr> RuntimeError: oops",
        ]

    def test_failed_strips_trailing_newline_no_phantom_continuation(self):
        plugin = make_plugin()
        result = make_result(host="db01", msg="single line\n")
        plugin.v2_runner_on_failed(result, ignore_errors=False)
        assert displayed_text(plugin) == ["failed | db01 | msg: single line"]

    def test_failed_with_rc_only(self):
        plugin = make_plugin()
        result = make_result(host="db01")
        result.result["rc"] = 1
        plugin.v2_runner_on_failed(result, ignore_errors=False)
        assert "failed | db01 | rc: 1" in displayed_text(plugin)

    def test_failed_emits_rc_alongside_msg(self):
        # rc must surface even when msg/stderr are present — exit codes are
        # diagnostic signal an agent can't recover from a sanitized message.
        plugin = make_plugin()
        result = make_result(host="db01", msg="killed")
        result.result["rc"] = 137
        plugin.v2_runner_on_failed(result, ignore_errors=False)
        assert "failed | db01 | msg: killed | rc: 137" in displayed_text(plugin)

    def test_failed_emits_rc_alongside_stderr(self):
        plugin = make_plugin()
        result = make_result(host="db01", stderr="boom")
        result.result["rc"] = 2
        plugin.v2_runner_on_failed(result, ignore_errors=False)
        assert "failed | db01 | stderr: boom | rc: 2" in displayed_text(plugin)

    def test_failed_emits_rc_alongside_msg_and_stderr(self):
        plugin = make_plugin()
        result = make_result(host="db01", msg="oops", stderr="err detail")
        result.result["rc"] = 1
        plugin.v2_runner_on_failed(result, ignore_errors=False)
        assert (
            "failed | db01 | msg: oops | stderr: err detail | rc: 1"
            in displayed_text(plugin)
        )

    def test_failed_multiline_with_rc(self):
        plugin = make_plugin()
        result = make_result(host="db01", stderr="err1\nerr2")
        result.result["rc"] = 1
        plugin.v2_runner_on_failed(result, ignore_errors=False)
        assert displayed_text(plugin) == [
            "failed | db01 | stderr: err1 | rc: 1",
            "stderr> err2",
        ]

    def test_failed_ignore_errors(self):
        plugin = make_plugin()
        result = make_result(host="db01", msg="expected failure")
        plugin.v2_runner_on_failed(result, ignore_errors=True)
        lines = displayed_text(plugin)
        assert "failed | db01 | msg: expected failure" in lines
        assert "...ignoring" in lines

    def test_failed_ignore_errors_ordering_after_continuations(self):
        # ...ignoring must come after the failure block (lead + continuations)
        # so an agent reading top-down sees the full failure before the marker.
        plugin = make_plugin()
        result = make_result(host="db01", msg="line1\nline2")
        plugin.v2_runner_on_failed(result, ignore_errors=True)
        assert displayed_text(plugin) == [
            "failed | db01 | msg: line1",
            "msg> line2",
            "...ignoring",
        ]

    def test_failed_no_details(self):
        plugin = make_plugin()
        result = make_result(host="db01")
        plugin.v2_runner_on_failed(result, ignore_errors=False)
        assert "failed | db01 | msg: (no details)" in displayed_text(plugin)


class TestRunnerUnreachable:
    def test_unreachable(self):
        plugin = make_plugin()
        result = make_result(host="db01", msg="SSH connection timeout")
        plugin.v2_runner_on_unreachable(result)
        assert "unreachable | db01 | SSH connection timeout" in displayed_text(plugin)

    def test_unreachable_multiline_emits_continuation(self):
        plugin = make_plugin()
        result = make_result(
            host="db01", msg="SSH timeout\nfatal: unable to reach host"
        )
        plugin.v2_runner_on_unreachable(result)
        assert displayed_text(plugin) == [
            "unreachable | db01 | SSH timeout",
            "msg> fatal: unable to reach host",
        ]

    def test_unreachable_no_msg(self):
        plugin = make_plugin()
        result = make_result(host="db01")
        plugin.v2_runner_on_unreachable(result)
        assert displayed_text(plugin) == ["unreachable | db01"]


class TestRunnerSkipped:
    def test_skipped_emits_nothing(self):
        plugin = make_plugin()
        result = make_result(host="web01")
        plugin.v2_runner_on_skipped(result)
        assert displayed_text(plugin) == []


class TestLoopItems:
    def test_item_ok_unchanged_emits_nothing(self):
        plugin = make_plugin()
        result = make_result(host="web01")
        result.result["item"] = "nginx"
        plugin.v2_runner_item_on_ok(result)
        assert displayed_text(plugin) == []

    def test_item_changed(self):
        plugin = make_plugin()
        result = make_result(host="web01", changed=True)
        result.result["item"] = "nginx"
        plugin.v2_runner_item_on_ok(result)
        assert "changed | web01 | item: nginx" in displayed_text(plugin)

    def test_item_failed(self):
        plugin = make_plugin()
        result = make_result(host="web01", msg="not found")
        result.result["item"] = "badpkg"
        plugin.v2_runner_item_on_failed(result)
        assert "failed | web01 | item: badpkg | msg: not found" in displayed_text(
            plugin
        )

    def test_item_failed_multiline_emits_continuation(self):
        plugin = make_plugin()
        result = make_result(host="web01", stderr="err1\nerr2")
        result.result["item"] = "badpkg"
        plugin.v2_runner_item_on_failed(result)
        assert displayed_text(plugin) == [
            "failed | web01 | item: badpkg | stderr: err1",
            "stderr> err2",
        ]

    def test_item_failed_emits_rc(self):
        plugin = make_plugin()
        result = make_result(host="web01", msg="bad pkg")
        result.result["item"] = "badpkg"
        result.result["rc"] = 1
        plugin.v2_runner_item_on_failed(result)
        assert "failed | web01 | item: badpkg | msg: bad pkg | rc: 1" in displayed_text(
            plugin
        )

    def test_item_skipped(self):
        plugin = make_plugin()
        result = make_result(host="web01")
        result.result["item"] = "nginx"
        plugin.v2_runner_item_on_skipped(result)
        assert displayed_text(plugin) == []


class TestRecap:
    def test_single_host_recap(self):
        plugin = make_plugin()
        stats = MagicMock()
        stats.processed = {"web01": {}}
        stats.summarize.return_value = {
            "ok": 3,
            "changed": 1,
            "unreachable": 0,
            "failures": 0,
            "skipped": 2,
            "rescued": 0,
            "ignored": 0,
        }
        stats.custom = {}
        plugin.v2_playbook_on_stats(stats)
        lines = displayed_text(plugin)
        assert len(lines) == 1
        assert lines[0] == "RECAP | web01: ok=3 changed=1 skipped=2"

    def test_multi_host_recap(self, monkeypatch):
        # Pin ANSIBLE_LOG_PATH so this test stays focused on RECAP formatting,
        # not on the conditional HINT line (covered in TestRecapHint).
        monkeypatch.setenv("ANSIBLE_LOG_PATH", "/tmp/ansible.log")
        plugin = make_plugin()
        stats = MagicMock()
        stats.processed = {"web01": {}, "db01": {}}

        def summarize(host):
            if host == "web01":
                return {
                    "ok": 3,
                    "changed": 1,
                    "unreachable": 0,
                    "failures": 0,
                    "skipped": 0,
                    "rescued": 0,
                    "ignored": 0,
                }
            return {
                "ok": 1,
                "changed": 0,
                "unreachable": 0,
                "failures": 1,
                "skipped": 0,
                "rescued": 0,
                "ignored": 0,
            }

        stats.summarize.side_effect = summarize
        stats.custom = {}
        plugin.v2_playbook_on_stats(stats)
        lines = displayed_text(plugin)
        assert len(lines) == 1
        assert "web01: ok=3 changed=1" in lines[0]
        assert "db01: ok=1 failed=1" in lines[0]
        assert lines[0].startswith("RECAP | ")

    def test_recap_omits_zero_counts(self):
        plugin = make_plugin()
        stats = MagicMock()
        stats.processed = {"web01": {}}
        stats.summarize.return_value = {
            "ok": 5,
            "changed": 0,
            "unreachable": 0,
            "failures": 0,
            "skipped": 0,
            "rescued": 0,
            "ignored": 0,
        }
        stats.custom = {}
        plugin.v2_playbook_on_stats(stats)
        lines = displayed_text(plugin)
        assert lines[0] == "RECAP | web01: ok=5"


class TestRecapHint:
    """HINT line surfaces the ANSIBLE_LOG_PATH escape hatch only when failures
    occurred and the user has not already opted in by setting the env var."""

    def _stats_with(self, **counts):
        defaults = {
            "ok": 0,
            "changed": 0,
            "unreachable": 0,
            "failures": 0,
            "skipped": 0,
            "rescued": 0,
            "ignored": 0,
        }
        defaults.update(counts)
        stats = MagicMock()
        stats.processed = {"db01": {}}
        stats.summarize.return_value = defaults
        stats.custom = {}
        return stats

    def test_hint_emitted_on_failures_when_log_path_unset(self, monkeypatch):
        monkeypatch.delenv("ANSIBLE_LOG_PATH", raising=False)
        plugin = make_plugin()
        plugin.v2_playbook_on_stats(self._stats_with(ok=1, failures=1))
        lines = displayed_text(plugin)
        assert any(line.startswith("HINT | ") for line in lines)
        assert any("ANSIBLE_LOG_PATH" in line for line in lines)

    def test_hint_emitted_on_unreachable_when_log_path_unset(self, monkeypatch):
        monkeypatch.delenv("ANSIBLE_LOG_PATH", raising=False)
        plugin = make_plugin()
        plugin.v2_playbook_on_stats(self._stats_with(unreachable=1))
        lines = displayed_text(plugin)
        assert any(line.startswith("HINT | ") for line in lines)

    def test_hint_not_emitted_when_log_path_set(self, monkeypatch):
        monkeypatch.setenv("ANSIBLE_LOG_PATH", "/tmp/ansible.log")
        plugin = make_plugin()
        plugin.v2_playbook_on_stats(self._stats_with(ok=1, failures=1))
        lines = displayed_text(plugin)
        assert not any(line.startswith("HINT | ") for line in lines)

    def test_hint_emitted_when_log_path_empty_string(self, monkeypatch):
        # Empty string matches Ansible's own semantics for "logging disabled" —
        # treat as unset so the agent still sees the escape hatch.
        monkeypatch.setenv("ANSIBLE_LOG_PATH", "")
        plugin = make_plugin()
        plugin.v2_playbook_on_stats(self._stats_with(ok=1, failures=1))
        lines = displayed_text(plugin)
        assert any(line.startswith("HINT | ") for line in lines)

    def test_hint_not_emitted_on_clean_run(self, monkeypatch):
        monkeypatch.delenv("ANSIBLE_LOG_PATH", raising=False)
        plugin = make_plugin()
        plugin.v2_playbook_on_stats(self._stats_with(ok=5, changed=1))
        lines = displayed_text(plugin)
        assert not any(line.startswith("HINT | ") for line in lines)
        assert len(lines) == 1  # just RECAP

    def test_hint_emitted_after_recap(self, monkeypatch):
        monkeypatch.delenv("ANSIBLE_LOG_PATH", raising=False)
        plugin = make_plugin()
        plugin.v2_playbook_on_stats(self._stats_with(ok=1, failures=1))
        lines = displayed_text(plugin)
        assert lines[0].startswith("RECAP | ")
        assert lines[1].startswith("HINT | ")


class TestTokenEfficiency:
    """Structural assertions on the compression contract.

    These pin the project's core promise — that agent token usage stays
    bounded — by asserting per-event output line counts for representative
    scenarios. If a future change leaks output, these break first.
    """

    def test_hundred_ok_unchanged_emits_zero_lines(self):
        plugin = make_plugin()
        for _ in range(100):
            plugin.v2_runner_on_ok(make_result(host="web01", changed=False))
        assert displayed_text(plugin) == []

    def test_hundred_skipped_emits_zero_lines(self):
        plugin = make_plugin()
        for _ in range(100):
            plugin.v2_runner_on_skipped(make_result(host="web01"))
        assert displayed_text(plugin) == []

    def test_changed_is_exactly_one_line_per_result(self):
        plugin = make_plugin()
        for i in range(50):
            plugin.v2_runner_on_ok(make_result(host=f"web{i:02d}", changed=True))
        assert len(displayed_text(plugin)) == 50

    def test_failure_block_line_count_matches_stderr_line_count(self):
        # An N-line stderr should produce exactly N output lines:
        # 1 lead + (N-1) continuations. No amplification.
        plugin = make_plugin()
        stderr = "\n".join(f"line{i}" for i in range(20))
        result = make_result(host="db01", stderr=stderr)
        plugin.v2_runner_on_failed(result, ignore_errors=False)
        assert len(displayed_text(plugin)) == 20

    def test_clean_run_collapses_to_single_recap_line(self, monkeypatch):
        # The headline promise: a fully successful playbook = 1 line.
        monkeypatch.setenv("ANSIBLE_LOG_PATH", "")
        plugin = make_plugin()
        for _ in range(50):
            plugin.v2_runner_on_ok(make_result(host="web01", changed=False))
            plugin.v2_runner_on_skipped(make_result(host="web01"))
        stats = MagicMock()
        stats.processed = {"web01": {}}
        stats.summarize.return_value = {
            "ok": 50,
            "changed": 0,
            "unreachable": 0,
            "failures": 0,
            "skipped": 50,
            "rescued": 0,
            "ignored": 0,
        }
        plugin.v2_playbook_on_stats(stats)
        assert len(displayed_text(plugin)) == 1
        assert displayed_text(plugin)[0].startswith("RECAP | ")

    def test_continuation_prefix_is_minimal(self):
        # Every byte counts on the failure path. The prefix must not creep
        # back to a leading-indent form like "  msg> " (5 extra bytes/line).
        plugin = make_plugin()
        result = make_result(host="db01", msg="a\nb\nc")
        plugin.v2_runner_on_failed(result, ignore_errors=False)
        for line in displayed_text(plugin)[1:]:
            assert line.startswith(("msg> ", "stderr> ")), (
                f"continuation line gained extra prefix: {line!r}"
            )


def _stats(failures=1, unreachable=0, ok=1):
    stats = MagicMock()
    stats.processed = {"db01": {}}
    stats.summarize.return_value = {
        "ok": ok,
        "changed": 0,
        "unreachable": unreachable,
        "failures": failures,
        "skipped": 0,
        "rescued": 0,
        "ignored": 0,
    }
    stats.custom = {}
    return stats


def _read_details(path):
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


class TestFailureDetails:
    """The companion <ANSIBLE_LOG_PATH>.details.jsonl file that makes the
    escape hatch actually deliver full detail."""

    def test_log_pointer_and_full_detail_on_failure(self, monkeypatch, tmp_path):
        details = str(tmp_path / "ansible.log") + ".details.jsonl"
        monkeypatch.setenv("ANSIBLE_LOG_PATH", str(tmp_path / "ansible.log"))
        plugin = make_plugin()

        plugin.v2_playbook_on_task_start(make_task("Configure nginx"), False)
        result = make_result(host="db01", msg="Permission denied", stderr="denied")
        # Detail the trimmed on-screen lines never carry.
        result.result.update({"rc": 13, "cmd": "systemctl restart nginx", "stdout": ""})
        plugin.v2_runner_on_failed(result, ignore_errors=False)
        plugin.v2_playbook_on_stats(_stats())

        lines = displayed_text(plugin)
        assert lines[-1] == f"LOG | {details}"
        assert not any(line.startswith("HINT | ") for line in lines)

        rec = _read_details(details)[0]
        assert rec["status"] == "failed"
        assert rec["host"] == "db01"
        assert rec["task"] == "Configure nginx"
        assert rec["result"]["rc"] == 13
        assert rec["result"]["cmd"] == "systemctl restart nginx"
        assert rec["result"]["msg"] == "Permission denied"

    def test_log_pointer_takes_precedence_over_hint(self, monkeypatch, tmp_path):
        # A real failure with a log path set: agents get the LOG pointer, not a
        # HINT telling them to set the path they already set.
        monkeypatch.setenv("ANSIBLE_LOG_PATH", str(tmp_path / "ansible.log"))
        plugin = make_plugin()
        plugin.v2_playbook_on_task_start(make_task("T"), False)
        plugin.v2_runner_on_failed(
            make_result(host="db01", msg="x"), ignore_errors=False
        )
        plugin.v2_playbook_on_stats(_stats())
        lines = displayed_text(plugin)
        assert any(line.startswith("LOG | ") for line in lines)
        assert not any(line.startswith("HINT | ") for line in lines)

    def test_hint_when_failure_and_no_log_path(self, monkeypatch, tmp_path):
        # No log path: nothing is written and the HINT points at the escape hatch.
        plugin = make_plugin()
        plugin.v2_playbook_on_task_start(make_task("T"), False)
        plugin.v2_runner_on_failed(
            make_result(host="db01", msg="x"), ignore_errors=False
        )
        plugin.v2_playbook_on_stats(_stats())
        lines = displayed_text(plugin)
        assert not any(line.startswith("LOG | ") for line in lines)
        assert any(line.startswith("HINT | ") for line in lines)
        assert not (tmp_path / "ansible.log.details.jsonl").exists()

    def test_detail_drops_invocation_and_internal_keys(self, monkeypatch, tmp_path):
        details = str(tmp_path / "ansible.log") + ".details.jsonl"
        monkeypatch.setenv("ANSIBLE_LOG_PATH", str(tmp_path / "ansible.log"))
        plugin = make_plugin()
        plugin.v2_playbook_on_task_start(make_task("Run"), False)
        result = make_result(host="db01", msg="boom")
        result.result.update(
            {
                "invocation": {"module_args": {"password": "s3cret"}},
                "_ansible_no_log": False,
                "_ansible_parsed": True,
            }
        )
        plugin.v2_runner_on_failed(result, ignore_errors=False)
        rec = _read_details(details)[0]
        assert "invocation" not in rec["result"]
        assert all(not k.startswith("_ansible_") for k in rec["result"])
        assert rec["result"]["msg"] == "boom"

    def test_unreachable_writes_detail(self, monkeypatch, tmp_path):
        details = str(tmp_path / "ansible.log") + ".details.jsonl"
        monkeypatch.setenv("ANSIBLE_LOG_PATH", str(tmp_path / "ansible.log"))
        plugin = make_plugin()
        plugin.v2_playbook_on_task_start(make_task("Ping"), False)
        plugin.v2_runner_on_unreachable(make_result(host="db01", msg="SSH timeout"))
        rec = _read_details(details)[0]
        assert rec["status"] == "unreachable"
        assert rec["result"]["msg"] == "SSH timeout"

    def test_item_failure_records_item(self, monkeypatch, tmp_path):
        details = str(tmp_path / "ansible.log") + ".details.jsonl"
        monkeypatch.setenv("ANSIBLE_LOG_PATH", str(tmp_path / "ansible.log"))
        plugin = make_plugin()
        plugin.v2_playbook_on_task_start(make_task("Install"), False)
        result = make_result(host="web01", msg="not found")
        result.result["item"] = "badpkg"
        plugin.v2_runner_item_on_failed(result)
        rec = _read_details(details)[0]
        assert rec["item"] == "badpkg"
        assert rec["status"] == "failed"

    def test_ignored_failure_recorded_as_ignored(self, monkeypatch, tmp_path):
        details = str(tmp_path / "ansible.log") + ".details.jsonl"
        monkeypatch.setenv("ANSIBLE_LOG_PATH", str(tmp_path / "ansible.log"))
        plugin = make_plugin()
        plugin.v2_playbook_on_task_start(make_task("Best effort"), False)
        plugin.v2_runner_on_failed(
            make_result(host="db01", msg="oops"), ignore_errors=True
        )
        assert _read_details(details)[0]["status"] == "ignored"

    def test_multiple_failures_appended(self, monkeypatch, tmp_path):
        details = str(tmp_path / "ansible.log") + ".details.jsonl"
        monkeypatch.setenv("ANSIBLE_LOG_PATH", str(tmp_path / "ansible.log"))
        plugin = make_plugin()
        plugin.v2_playbook_on_task_start(make_task("T"), False)
        plugin.v2_runner_on_failed(
            make_result(host="db01", msg="a"), ignore_errors=False
        )
        plugin.v2_runner_on_failed(
            make_result(host="db02", msg="b"), ignore_errors=False
        )
        assert [r["host"] for r in _read_details(details)] == ["db01", "db02"]

    def test_details_truncated_each_run(self, monkeypatch, tmp_path):
        details = str(tmp_path / "ansible.log") + ".details.jsonl"
        monkeypatch.setenv("ANSIBLE_LOG_PATH", str(tmp_path / "ansible.log"))
        first = make_plugin()
        first.v2_playbook_on_task_start(make_task("T"), False)
        first.v2_runner_on_failed(make_result(host="old", msg="x"), ignore_errors=False)
        # A fresh run (new instance) overwrites rather than appends.
        second = make_plugin()
        second.v2_playbook_on_task_start(make_task("T"), False)
        second.v2_runner_on_failed(
            make_result(host="new", msg="y"), ignore_errors=False
        )
        assert [r["host"] for r in _read_details(details)] == ["new"]

    def test_details_accumulate_across_playbooks(self, monkeypatch, tmp_path):
        # One `ansible-playbook a.yml b.yml` invocation shares one instance and
        # fires v2_playbook_on_start per playbook; records must accumulate.
        details = str(tmp_path / "ansible.log") + ".details.jsonl"
        monkeypatch.setenv("ANSIBLE_LOG_PATH", str(tmp_path / "ansible.log"))
        plugin = make_plugin()
        plugin.v2_playbook_on_start(MagicMock())
        plugin.v2_playbook_on_task_start(make_task("T1"), False)
        plugin.v2_runner_on_failed(
            make_result(host="db01", msg="x"), ignore_errors=True
        )
        plugin.v2_playbook_on_start(MagicMock())
        assert [r["host"] for r in _read_details(details)] == ["db01"]
        plugin.v2_playbook_on_task_start(make_task("T2"), False)
        plugin.v2_runner_on_failed(
            make_result(host="db02", msg="y"), ignore_errors=True
        )
        assert [r["host"] for r in _read_details(details)] == ["db01", "db02"]

    def test_stale_details_removed_at_start(self, monkeypatch, tmp_path):
        details = tmp_path / "ansible.log.details.jsonl"
        monkeypatch.setenv("ANSIBLE_LOG_PATH", str(tmp_path / "ansible.log"))
        failed = make_plugin()
        failed.v2_playbook_on_task_start(make_task("T"), False)
        failed.v2_runner_on_failed(
            make_result(host="db01", msg="x"), ignore_errors=False
        )
        assert details.exists()
        clean = make_plugin()
        clean.v2_playbook_on_start(MagicMock())
        assert not details.exists()

    def test_no_file_on_success(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ANSIBLE_LOG_PATH", str(tmp_path / "ansible.log"))
        details = tmp_path / "ansible.log.details.jsonl"
        plugin = make_plugin()
        plugin.v2_playbook_on_task_start(make_task("Configure"), False)
        plugin.v2_runner_on_ok(make_result(host="web01", changed=True))
        plugin.v2_playbook_on_stats(_stats(failures=0, ok=3))
        lines = displayed_text(plugin)
        assert all(not line.startswith("LOG | ") for line in lines)
        assert not details.exists()

    def test_write_failure_swallowed(self, monkeypatch, tmp_path):
        # Log path under a nonexistent directory: no crash, no LOG, and no HINT
        # (the user did set a path, so nudging them to set one would be wrong).
        monkeypatch.setenv(
            "ANSIBLE_LOG_PATH", str(tmp_path / "missing" / "ansible.log")
        )
        plugin = make_plugin()
        plugin.v2_playbook_on_task_start(make_task("T"), False)
        plugin.v2_runner_on_failed(
            make_result(host="db01", msg="x"), ignore_errors=False
        )
        plugin.v2_playbook_on_stats(_stats())
        lines = displayed_text(plugin)
        assert not any(line.startswith(("LOG | ", "HINT | ")) for line in lines)


class TestLogPathResolution:
    def test_prefers_env_var(self, monkeypatch):
        monkeypatch.setenv("ANSIBLE_LOG_PATH", "/tmp/from-env.log")
        monkeypatch.setattr(_module.C, "DEFAULT_LOG_PATH", "/tmp/from-cfg.log")
        assert make_plugin()._log_path() == "/tmp/from-env.log"

    def test_falls_back_to_ansible_cfg(self, monkeypatch):
        monkeypatch.setattr(_module.C, "DEFAULT_LOG_PATH", "/tmp/from-cfg.log")
        assert make_plugin()._log_path() == "/tmp/from-cfg.log"

    def test_expands_user(self, monkeypatch):
        monkeypatch.setenv("ANSIBLE_LOG_PATH", "~/ansible.log")
        assert make_plugin()._log_path() == os.path.expanduser("~/ansible.log")

    def test_details_path_derives_from_log_path(self, monkeypatch):
        monkeypatch.setenv("ANSIBLE_LOG_PATH", "/var/log/ansible.log")
        assert make_plugin()._details_path() == "/var/log/ansible.log.details.jsonl"

    def test_details_path_none_when_unset(self):
        assert make_plugin()._details_path() is None
