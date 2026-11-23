# Production Hardened Dockerfile for GreenCloud
FROM python:3.12-slim

# Create dedicated non-root application user
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

WORKDIR /app

# Install dependencies first for Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and assets
COPY engine/ ./engine/
COPY templates/ ./templates/
COPY static/ ./static/
COPY advisor.py app.py ./

# Secure directory ownership
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER 10001

EXPOSE 5000

# Container healthcheck for container engines
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/api/snapshot')" || exit 1

CMD ["python", "app.py"]
