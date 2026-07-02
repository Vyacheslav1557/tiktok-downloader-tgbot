# --- Build Stage ---
FROM python:3.11-slim AS builder

# Prevent Python from writing .pyc files and enable buffering
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install poetry
RUN pip install --no-cache-dir poetry poetry-plugin-export

# Copy only the dependency definition files
COPY pyproject.toml poetry.lock ./

# Export poetry dependencies to requirements.txt (only main)
RUN poetry export --without-hashes --only main -f requirements.txt -o requirements.txt

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt


# --- Final Stage ---
FROM python:3.11-slim AS runner

# Prevent Python from writing .pyc files and enable buffering
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Install ffmpeg with minimal dependencies and clean apt cache immediately
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the pre-built virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application source code
COPY api/ ./api/
COPY handlers.py logger.py main.py ./

# Create a non-root user for security and adjust permissions
RUN useradd -mr -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Run the telegram bot
CMD ["python", "main.py"]
