# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and
tracking starts at the current release.

## [0.3.3] - 2026-08-13

### Added

- Canonical clispec v0.3 schema and offline `capabilities` introspection.
- Structured JSON output, structured usage errors, and shell completions.
- CI conformance gate requiring a 24/24 Excellent score.

## [0.3.2](https://github.com/rvben/ansible-agent-callback/compare/v0.3.1...v0.3.2) - 2026-07-01

### Added

- capture full failure detail to a companion file ([cac582b](https://github.com/rvben/ansible-agent-callback/commit/cac582bb479473e4cc37b15b25f2af548a6d1cfa))

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
