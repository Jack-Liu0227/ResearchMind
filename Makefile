.PHONY: help install dev test lint format clean run demo web

# Default target
help:
	@echo "ResearchMind - 智能科研助手"
	@echo ""
	@echo "Available commands:"
	@echo "  install     Install dependencies"
	@echo "  dev         Install development dependencies"
	@echo "  verify      Verify installation"
	@echo "  test        Run tests"
	@echo "  lint        Run linting"
	@echo "  format      Format code"
	@echo "  clean       Clean cache and build files"
	@echo "  run         Run ResearchMind interactively"
	@echo "  demo        Run demo mode"
	@echo "  web         Start web interface"
	@echo "  lock        Update dependency lock file"

# Install dependencies
install:
	uv sync

# Install development dependencies
dev:
	uv sync --extra dev

# Install all dependencies (including docs, jupyter)
all:
	uv sync --extra all

# Verify installation
verify:
	uv run python scripts/verify_installation.py

# Run tests
test:
	uv run python test_agents.py

# Run pytest (if available)
pytest:
	uv run pytest

# Run linting
lint:
	uv run flake8 agents/ mcp_servers/ main_mcp.py test_agents.py
	uv run mypy agents/ mcp_servers/ main_mcp.py

# Format code
format:
	uv run black agents/ mcp_servers/ main_mcp.py test_agents.py
	uv run isort agents/ mcp_servers/ main_mcp.py test_agents.py

# Clean cache and build files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .coverage

# Run ResearchMind interactively
run:
	uv run python main_mcp.py --interactive

# Run demo mode
demo:
	uv run python main_mcp.py --demo

# Start web interface
web:
	uv run python main_mcp.py --web --port 8080

# Research with specific topic
research:
	@read -p "Enter research topic: " topic; \
	uv run python main_mcp.py --research "$$topic" --workflow hybrid

# Update lock file
lock:
	uv lock

# Show project info
info:
	uv tree
	@echo ""
	@echo "Python version:"
	uv run python --version
	@echo ""
	@echo "Project structure:"
	@find . -name "*.py" -not -path "./.*" -not -path "./src/*" | head -20

# Build package
build:
	uv build

# Install in editable mode
editable:
	uv pip install -e .

# Show outdated packages
outdated:
	uv pip list --outdated
