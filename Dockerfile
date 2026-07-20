FROM python:3.11-slim

WORKDIR /app

# Install build dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python package and dependencies
COPY pyproject.toml /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Copy application source code and migrations
COPY fantomex /app/fantomex
COPY alembic.ini /app/
COPY alembic /app/alembic

# Create persistent storage folder
RUN mkdir -p /app/data

# Setup default runtime environment variables
ENV HOST=0.0.0.0
ENV PORT=8000
ENV DATABASE_URL=sqlite:////app/data/fantomex.db
ENV ARTIFACT_ROOT=/app/data/artifacts

EXPOSE 8000

# Perform database migrations on startup and start the server
CMD ["sh", "-c", "python -m alembic upgrade head && python -m fantomex.server"]
