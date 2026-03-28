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
