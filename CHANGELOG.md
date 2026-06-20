# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and
tracking starts at the current release.

## [0.3.1] - 2026-03-28

Token-optimized Ansible stdout callback plugin for AI coding agents, reducing
default output by 70-90% on clean runs.

### Added

- Asymmetric compression: clean runs collapse to a single `RECAP` line, while
  failures preserve full `msg>` / `stderr>` continuation lines, `rc`, and a
  `HINT` pointing at `ANSIBLE_LOG_PATH` for the complete log.
- `ok` and `skipped` tasks produce no output; comment-only diff changes are
  skipped and per-task totals appended.
- `install`, `uninstall`, `update`, and `env` CLI commands to configure the
  plugin for Claude Code, Codex CLI, Gemini CLI, and a generic shell.
- Output-volume benchmark harness (`make bench`) and structural compression
  tests.
