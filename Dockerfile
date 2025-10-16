# ResearchMind Backend Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files and README
COPY pyproject.toml uv.lock README.md ./

# Install Python dependencies using UV
RUN uv sync --no-dev --frozen

# Copy application code
COPY agents ./agents
COPY mcp_servers ./mcp_servers
COPY services ./services
COPY main.py ./

# Create necessary directories
RUN mkdir -p session_data/images session_data/metadata session_data/structures

# Set Python path to use virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Expose ports
EXPOSE 50001 50002 50003 50004 50005

# Health check (using python instead of curl to avoid dependency)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:50001/api/health')" || exit 1

# Default command
CMD ["python", "main.py"]

