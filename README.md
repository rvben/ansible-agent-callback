# ansible-agent-callback

[![codecov](https://codecov.io/gh/rvben/ansible-agent-callback/graph/badge.svg)](https://codecov.io/gh/rvben/ansible-agent-callback)

Token-optimized Ansible stdout callback plugin for AI coding agents.
**Reduces output by 70-90%** compared to the default callback.

Compression is asymmetric on purpose:

- **Success path:** aggressive — clean runs collapse to a single `RECAP`
  line; ok and skipped tasks produce zero output.
- **Failure path:** readable — full stack traces stay intact via
  `msg> ` / `stderr> ` continuation lines, plus `rc` and a `HINT`
  pointing at `ANSIBLE_LOG_PATH` for the full log. Still smaller than
  default, but optimized for diagnosis over byte count.

Verified on a mixed-shape fixture (12 ok, 3 changed, 3 skipped, 2 ignored
failures, 1 loop) — see [`bench/`](bench/) and run `make bench` to
reproduce:

| Metric | default | agent | Reduction |
|--------|---------|-------|-----------|
| bytes  | 3,174   | 499   | **84.3%** |
| lines  | 90      | 15    | **83.3%** |
| words  | 286     | 79    | **72.4%** |

Clean runs (zero changes, zero failures) collapse to a single line
regardless of task count, so the reduction approaches the default's
total volume the larger your playbook.

## Getting Started

Install the plugin and configure your AI coding agents in one command:

```bash
uvx ansible-agent-callback install
```

This will:

1. Copy the callback plugin to `~/.ansible/plugins/callback/`
2. Detect which AI coding agents you have installed
3. Let you pick which ones to configure (detected agents are pre-selected)

To skip the interactive selector and configure everything automatically:

```bash
uvx ansible-agent-callback install --all
```

That's it. Your agents will now use the token-optimized output when running Ansible.

## Output Format

Only changed, failed, and unreachable results are shown.
Ok and skipped tasks produce zero output.
A fully successful playbook run outputs just the RECAP line.

```text
PLAY | Configure webservers
TASK | Configure nginx
changed | web01 | diff: +worker_processes 4;
failed | db01 | msg: Permission denied | rc: 1
RECAP | web01: ok=3 changed=1 | db01: ok=1 failed=1
```

### Diff summaries

For changed tasks with diff data, the plugin shows the first
non-comment change line. Comment-only changes (`#` or `;` prefix)
are skipped so the agent isn't misled by `-# old comment` while the
real edit is buried below. Multi-line diffs append `(+N -M)` totals
to signal there's more context:

```text
changed | web01 | diff: -workers 2
changed | web02 | diff: +listen 443 (+3 -1)
```

### Failures with multi-line output

Stack traces stay readable. The lead `failed` line carries a
single-line summary plus `rc`; remaining content emits as
continuation lines prefixed with `msg> ` or `stderr> `:

```text
failed | db01 | stderr: Traceback (most recent call last): | rc: 1
stderr>   File "/opt/app/run.py", line 5, in <module>
stderr>     do_thing()
stderr> RuntimeError: oops
```

The prefix is unambiguous (real output never produces it) and
grep-friendly: `^failed` finds every failure, and an agent reads
forward until the next non-continuation line for the full block.

## Full Output When Things Fail

The compressed format keeps successful runs token-cheap, but agents
sometimes need the full picture to diagnose a failure. Ansible's own
`ANSIBLE_LOG_PATH` is the escape hatch:

```bash
ANSIBLE_LOG_PATH=/tmp/ansible.log ansible-playbook site.yml
```

The plugin keeps emitting its compressed output to stdout; Ansible
writes the unfiltered default-format log to the path you set. Agents
can `grep` or `tail` it on demand without paying the token cost up
front.

When a run has failures or unreachable hosts and `ANSIBLE_LOG_PATH`
is not set, the plugin appends a single `HINT` line after the RECAP
to surface this escape hatch at the moment it's actually useful:

```text
RECAP | db01: ok=1 failed=1
HINT | set ANSIBLE_LOG_PATH=<path> and re-run for full output
```

Clean runs stay clean — no hint, no extra lines.

## Commands

```bash
ansible-agent-callback install              # Install plugin + configure agents
ansible-agent-callback install --all        # Auto-configure detected agents
ansible-agent-callback install --agents claude-code,codex-cli
ansible-agent-callback install --plugin-only # Just the plugin, no agent config
ansible-agent-callback update               # Update plugin to latest version
ansible-agent-callback uninstall            # Remove plugin + agent configs
ansible-agent-callback env                  # Print export for other agents
```

## Supported Agents

| Agent | Config |
|-------|--------|
| Claude Code | `~/.claude/settings.json` |
| Codex CLI | `~/.codex/config.toml` |
| Gemini CLI | `~/.gemini/.env` |
| Shell profile | `~/.zshrc` or `~/.bashrc` |
| Ansible global | `~/.ansible.cfg` |

## Development

```bash
make dev    # Install in editable mode
make test   # Run tests
make bench  # Compare default vs agent callback output volume
make build  # Build package
```
