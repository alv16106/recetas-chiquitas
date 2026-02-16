# Production Dockerfile for Recetas Chiquitas
# Use buildx to build for both platforms: docker buildx build --platform linux/amd64,linux/arm64 -t ... --push .
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    apt-get update && \
    apt-get install -y wget && \
    rm -rf /var/lib/apt/lists/*

# Copy application
COPY app/ ./app/
COPY config.py .
COPY run.py .
COPY scripts/ ./scripts/
COPY docker-entrypoint.sh .

# Entrypoint: create tables and seed before starting
RUN chmod +x docker-entrypoint.sh

# Create non-root user
RUN adduser --disabled-password --gecos "" appuser && \
    mkdir -p instance uploads certs && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 5000

RUN wget https://truststore.pki.rds.amazonaws.com/eu-west-2/eu-west-2-bundle.pem && \
    mv eu-west-2-bundle.pem ./certs/eu-west-2-bundle.pem

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 4 run:app"]
