# ansible-agent-callback

Token-optimized Ansible stdout callback plugin for AI coding agents. Reduces output by 70-90% compared to the default callback.

## Quick Start

```bash
uvx ansible-agent-callback install
```

This installs the callback plugin and interactively configures your AI coding agents (Claude Code, Codex CLI, Gemini CLI, etc.).

## Usage

```bash
# Via environment variable
ANSIBLE_STDOUT_CALLBACK=agent ansible-playbook site.yml

# Or configure permanently via the installer
```

## Output Format

One line per event, pipe-delimited:

```
PLAY | Configure webservers
TASK | Install nginx
ok | web01
changed | web02 | diff: +worker_processes 4;
failed | db01 | msg: Permission denied
RECAP | web01: ok=3 changed=1 | db01: ok=1 failed=1
```

- Skipped tasks are hidden
- No color codes or decorative formatting
- Full details only on failures

## Commands

```bash
ansible-agent-callback install              # Install plugin + configure agents
ansible-agent-callback install --plugin-only # Just the plugin
ansible-agent-callback install --all        # Auto-configure detected agents
ansible-agent-callback install --agents claude-code,codex-cli
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
make build  # Build package
```
