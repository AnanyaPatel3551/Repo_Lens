FROM python:3.12-slim

# Install system dependencies, specifically git (required for repository cloning)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency definition and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend codebase
COPY src/ ./src
COPY main.py .

# Expose FastAPI default port
EXPOSE 8000

# Set environment variable defaults
ENV PORT=8000
ENV HOST=0.0.0.0

# Start FastAPI application
CMD ["sh", "-c", "uvicorn main:app --host $HOST --port $PORT"]
