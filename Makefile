PLUGIN_NAME := agent
PLUGIN_SRC := callback_plugins/$(PLUGIN_NAME).py
INSTALL_DIR := $(HOME)/.ansible/plugins/callback

.PHONY: install uninstall test lint fmt build dev

install: $(PLUGIN_SRC)
	@mkdir -p $(INSTALL_DIR)
	cp $(PLUGIN_SRC) $(INSTALL_DIR)/$(PLUGIN_NAME).py
	@echo "Installed to $(INSTALL_DIR)/$(PLUGIN_NAME).py"

uninstall:
	rm -f $(INSTALL_DIR)/$(PLUGIN_NAME).py
	@echo "Removed $(INSTALL_DIR)/$(PLUGIN_NAME).py"

test:
	uv run --with pytest --with ansible-core pytest tests/ -v

lint:
	python3 -m py_compile callback_plugins/agent.py
	python3 -m py_compile src/ansible_agent_callback/plugin.py
	uvx ruff check .
	uvx ruff format --check .

fmt:
	uvx ruff check --fix .
	uvx ruff format .

build:
	uv build

dev:
	uv pip install -e .
