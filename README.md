# ansible-agent-callback

Token-optimized Ansible stdout callback plugin for AI agent consumption.

## Install

```bash
make install
```

This copies `agent.py` to `~/.ansible/plugins/callback/`.

## Usage

```bash
# Via environment variable
ANSIBLE_STDOUT_CALLBACK=agent ansible-playbook site.yml

# Or in ansible.cfg
[defaults]
stdout_callback = agent
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

## Uninstall

```bash
make uninstall
```
