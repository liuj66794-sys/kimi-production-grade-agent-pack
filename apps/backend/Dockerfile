# Kimi Agent Pack Dashboard API — Production Dockerfile
# Targets: Render, Railway, Fly.io, AWS ECS, etc.

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (git for script execution, build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements first (layer caching)
COPY apps/backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire repo (backend needs access to scripts/, schemas/, agents/, etc.)
COPY . /app

# Set working directory to backend for imports
WORKDIR /app/apps/backend

# Environment defaults (override in platform dashboard)
ENV PYTHONPATH=/app/apps/backend
ENV PYTHONUNBUFFERED=1

# Expose FastAPI port
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Start uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
