# ansible-agent-callback

Token-optimized Ansible stdout callback plugin for AI coding agents.
Reduces output by 70-90% compared to the default callback.

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
failed | db01 | msg: Permission denied
RECAP | web01: ok=3 changed=1 | db01: ok=1 failed=1
```

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
make build  # Build package
```
