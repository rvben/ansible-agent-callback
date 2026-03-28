PLUGIN_NAME := agent
PLUGIN_SRC := callback_plugins/$(PLUGIN_NAME).py
INSTALL_DIR := $(HOME)/.ansible/plugins/callback

.PHONY: install uninstall test lint

install: $(PLUGIN_SRC)
	@mkdir -p $(INSTALL_DIR)
	cp $(PLUGIN_SRC) $(INSTALL_DIR)/$(PLUGIN_NAME).py
	@echo "Installed to $(INSTALL_DIR)/$(PLUGIN_NAME).py"

uninstall:
	rm -f $(INSTALL_DIR)/$(PLUGIN_NAME).py
	@echo "Removed $(INSTALL_DIR)/$(PLUGIN_NAME).py"

test:
	python -m pytest tests/ -v

lint:
	python -m py_compile callback_plugins/agent.py
