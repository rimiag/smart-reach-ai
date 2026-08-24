# =============================================================================
# Backend Dockerfile - AI Lead Generation Platform
# =============================================================================

FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    default-libmysqlclient-dev \
    pkg-config \
    xmlsec1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
# Exclude .env file - docker-compose will provide env vars
COPY . .

# Remove .env if it exists (docker-compose provides env vars)
RUN if [ -f .env ]; then mv .env .env.local.example; fi

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/exports /app/uploads /app/celerybeat && \
    chmod 755 /app/logs /app/exports /app/uploads /app/celerybeat

# Copy entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Create a non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app /app/logs /app/exports /app/uploads /app/celerybeat
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Set entrypoint to run migrations before starting
ENTRYPOINT ["docker-entrypoint.sh"]

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
