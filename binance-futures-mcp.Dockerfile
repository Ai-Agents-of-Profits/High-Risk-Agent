FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies 
RUN pip install --no-cache-dir ccxt mcp openai requests aiohttp pandas numpy

# Set environment variables for verbose logging
ENV PYTHONUNBUFFERED=1
ENV LOGLEVEL=DEBUG

# Create InitializationOptions class directly in the mcp server module
RUN echo '"""Patch for InitializationOptions class"""\n\
class InitializationOptions:\n\
    """Class to hold initialization options for MCP server"""\n\
    def __init__(self, port=None, host=None, server_name=None, stdio=False, custom_model_callbacks=None, server_version=None, capabilities=None, instructions=None):\n\
        self.port = port\n\
        self.host = host\n\
        self.server_name = server_name\n\
        self.stdio = stdio\n\
        self.custom_model_callbacks = custom_model_callbacks\n\
        self.server_version = server_version\n\
        self.capabilities = capabilities\n\
        self.instructions = instructions\n\
' > /usr/local/lib/python3.11/site-packages/mcp/server/initialization_options.py

# Make the InitializationOptions class available in the mcp.server namespace
RUN echo '\nfrom mcp.server.initialization_options import InitializationOptions\n' >> /usr/local/lib/python3.11/site-packages/mcp/server/__init__.py

# This image will be used with a volume mount to access the actual server code
