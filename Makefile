# ResearchMind Docker Management Makefile
# Provides convenient commands for managing Docker deployment

.PHONY: help build up down restart logs ps clean clean-all health

# Default target
help:
	@echo "ResearchMind Docker Management Commands"
	@echo "========================================"
	@echo ""
	@echo "Setup:"
	@echo "  make setup          - Initial setup (copy .env.example to .env)"
	@echo "  make build          - Build Docker images"
	@echo "  make build-nc       - Build Docker images without cache"
	@echo ""
	@echo "Service Management:"
	@echo "  make up             - Start all services"
	@echo "  make down           - Stop all services"
	@echo "  make restart        - Restart all services"
	@echo "  make ps             - Show service status"
	@echo ""
	@echo "Logs:"
	@echo "  make logs           - Show logs from all services"
	@echo "  make logs-f         - Follow logs from all services"
	@echo "  make logs-backend   - Show backend logs"
	@echo "  make logs-mcp       - Show MCP server logs"
	@echo ""
	@echo "Health & Monitoring:"
	@echo "  make health         - Check service health"
	@echo "  make stats          - Show container resource usage"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean          - Stop services and remove containers"
	@echo "  make clean-all      - Stop services, remove containers and volumes"
	@echo "  make prune          - Remove unused Docker resources"
	@echo ""
	@echo "Development:"
	@echo "  make shell-backend  - Open shell in backend container"
	@echo "  make shell-frontend - Open shell in frontend container"
	@echo ""

# Setup
setup:
	@echo "Setting up environment..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ Created .env file from .env.example"; \
		echo "⚠️  Please edit .env and add your API keys!"; \
	else \
		echo "✅ .env file already exists"; \
	fi

# Build
build:
	@echo "Building Docker images..."
	docker-compose build

build-nc:
	@echo "Building Docker images without cache..."
	docker-compose build --no-cache

# Service Management
up:
	@echo "Starting ResearchMind services..."
	docker-compose up -d
	@echo "✅ Services started"
	@echo "Frontend: http://localhost"
	@echo "API Docs: http://localhost:8000/docs"

down:
	@echo "Stopping ResearchMind services..."
	docker-compose down
	@echo "✅ Services stopped"

restart:
	@echo "Restarting ResearchMind services..."
	docker-compose restart
	@echo "✅ Services restarted"

ps:
	@echo "Service Status:"
	@docker-compose ps

# Logs
logs:
	docker-compose logs

logs-f:
	docker-compose logs -f

logs-backend:
	docker-compose logs -f backend

logs-mcp:
	docker-compose logs -f paper-search-mcp database-mcp simulation-mcp

logs-frontend:
	docker-compose logs -f frontend

# Health & Monitoring
health:
	@echo "Checking service health..."
	@echo ""
	@echo "Backend:"
	@curl -f http://localhost:8000/api/health 2>/dev/null && echo " ✅" || echo " ❌"
	@echo ""
	@echo "Paper Search MCP:"
	@curl -f http://localhost:50001/health 2>/dev/null && echo " ✅" || echo " ❌"
	@echo ""
	@echo "Database MCP:"
	@curl -f http://localhost:5002/health 2>/dev/null && echo " ✅" || echo " ❌"
	@echo ""
	@echo "Simulation MCP:"
	@curl -f http://localhost:5003/health 2>/dev/null && echo " ✅" || echo " ❌"
	@echo ""
	@echo "Frontend:"
	@curl -f http://localhost/health.html 2>/dev/null && echo " ✅" || echo " ❌"
	@echo ""

stats:
	docker stats --no-stream

# Cleanup
clean:
	@echo "Stopping services and removing containers..."
	docker-compose down
	@echo "✅ Cleanup complete"

clean-all:
	@echo "Stopping services and removing containers and volumes..."
	docker-compose down -v
	@echo "✅ Full cleanup complete"

prune:
	@echo "Removing unused Docker resources..."
	docker system prune -f
	@echo "✅ Prune complete"

# Development
shell-backend:
	docker-compose exec backend bash

shell-frontend:
	docker-compose exec frontend sh

shell-paper-search:
	docker-compose exec paper-search-mcp bash

shell-database:
	docker-compose exec database-mcp bash

shell-simulation:
	docker-compose exec simulation-mcp bash

# Quick start (setup + build + up)
quickstart: setup build up
	@echo ""
	@echo "🎉 ResearchMind is starting!"
	@echo "Please wait 1-2 minutes for all services to be ready"
	@echo ""
	@echo "Access:"
	@echo "  Frontend: http://localhost"
	@echo "  API Docs: http://localhost:8000/docs"
	@echo ""
	@echo "Check status with: make ps"
	@echo "View logs with: make logs-f"

