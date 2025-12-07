VENV_DIR := .venv
PYTHON := $(VENV_DIR)/bin/python
RUFF := $(VENV_DIR)/bin/ruff

.PHONY: venv install lock run clean

# Create virtual environment if it doesn't exist
venv:
	@test -d $(VENV_DIR) || uv venv

# Install from pyproject.toml (using lockfile if exists)
install: venv
	uv pip compile pyproject.toml -o requirements.lock
	uv pip install -r requirements.lock
	uv pip install -e ".[dev]"

# Lock dependencies from pyproject.toml
lock:
	@echo "🔐 Locking dependencies..."
	uv pip compile pyproject.toml -o requirements.lock

# Run your app (edit entry point as needed)
run:
	$(PYTHON) -m src.main

# Clean virtual environment and lockfile
clean:
	rm -rf $(VENV_DIR) requirements.lock

format:
	@echo "🎨 Formatting code..."
	$(RUFF) format src
	$(RUFF) check --fix src
