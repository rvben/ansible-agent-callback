PLUGIN_NAME := agent
PLUGIN_SRC := callback_plugins/$(PLUGIN_NAME).py
INSTALL_DIR := $(HOME)/.ansible/plugins/callback

.PHONY: install uninstall test lint fmt build dev bench check release-patch release-minor release-major

install: $(PLUGIN_SRC)
	@mkdir -p $(INSTALL_DIR)
	cp $(PLUGIN_SRC) $(INSTALL_DIR)/$(PLUGIN_NAME).py
	@echo "Installed to $(INSTALL_DIR)/$(PLUGIN_NAME).py"

uninstall:
	rm -f $(INSTALL_DIR)/$(PLUGIN_NAME).py
	@echo "Removed $(INSTALL_DIR)/$(PLUGIN_NAME).py"

test:
	uv run pytest tests/ -v

lint:
	python3 -m py_compile callback_plugins/agent.py
	python3 -m py_compile src/ansible_agent_callback/plugin.py
	uv run ruff check .
	uv run ruff format --check .

fmt:
	uv run ruff check --fix .
	uv run ruff format .

build:
	uv build

dev:
	uv pip install -e .

bench:
	uv run python bench/run.py

check: lint test

release-patch:
	vership bump patch

release-minor:
	vership bump minor

release-major:
	vership bump major
