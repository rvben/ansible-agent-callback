"""Tests for the agent callback plugin."""

import sys
import os
from unittest.mock import MagicMock

# Support both callback_plugins (local dev) and src layout
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "callback_plugins"))
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "src", "ansible_agent_callback")
)

try:
    import agent as _module
except ImportError:
    import plugin as _module


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

    def test_ok_changed_with_diff(self):
        plugin = make_plugin()
        diff = {"before": "workers 2\n", "after": "workers 4\n"}
        result = make_result(host="web01", changed=True, diff=diff)
        plugin.v2_runner_on_ok(result)
        lines = displayed_text(plugin)
        assert any("changed | web01 | diff: -workers 2" in line for line in lines)

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

    def test_failed_multiline_msg_joined(self):
        plugin = make_plugin()
        result = make_result(host="db01", msg="line1\nline2\nline3")
        plugin.v2_runner_on_failed(result, ignore_errors=False)
        assert r"failed | db01 | msg: line1\nline2\nline3" in displayed_text(plugin)

    def test_failed_multiline_stderr_joined(self):
        plugin = make_plugin()
        result = make_result(host="db01", msg="failed", stderr="err1\nerr2\nerr3")
        plugin.v2_runner_on_failed(result, ignore_errors=False)
        assert (
            r"failed | db01 | msg: failed | stderr: err1\nerr2\nerr3"
            in displayed_text(plugin)
        )

    def test_failed_with_rc_only(self):
        plugin = make_plugin()
        result = make_result(host="db01")
        result.result["rc"] = 1
        plugin.v2_runner_on_failed(result, ignore_errors=False)
        assert "failed | db01 | rc: 1" in displayed_text(plugin)

    def test_failed_ignore_errors(self):
        plugin = make_plugin()
        result = make_result(host="db01", msg="expected failure")
        plugin.v2_runner_on_failed(result, ignore_errors=True)
        lines = displayed_text(plugin)
        assert "failed | db01 | msg: expected failure" in lines
        assert "...ignoring" in lines


class TestRunnerUnreachable:
    def test_unreachable(self):
        plugin = make_plugin()
        result = make_result(host="db01", msg="SSH connection timeout")
        plugin.v2_runner_on_unreachable(result)
        assert "unreachable | db01 | SSH connection timeout" in displayed_text(plugin)


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

    def test_multi_host_recap(self):
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
