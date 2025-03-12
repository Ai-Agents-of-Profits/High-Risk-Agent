FROM python:3.11-slim

WORKDIR /app

# Install basic dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir ccxt mcp openai requests aiohttp pandas numpy matplotlib scikit-learn

# This image will be used with a volume mount to access the actual server code
