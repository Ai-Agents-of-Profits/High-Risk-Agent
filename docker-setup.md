# Docker Setup for MCP Servers

This guide explains how to use Docker with the crypto trading agent to resolve Python version compatibility issues.

## Prerequisites

- Docker Desktop installed and running
- Source code for both MCP servers:
  - Crypto MCP server at `c:\Users\mac\Documents\mcp-server-ccxt-main`
  - Binance Futures MCP server at `c:\Users\mac\Documents\biance-mcp\binance-futures-mcp`

## Building Docker Images

1. Build the Crypto MCP Docker image:
   ```bash
   docker build -t crypto-mcp:latest -f crypto-mcp.Dockerfile .
   ```

2. Build the Binance Futures MCP Docker image:
   ```bash
   docker build -t binance-futures-mcp:latest -f binance-futures-mcp.Dockerfile .
   ```

## Configuration

The `mcp_config.json` file is configured to use Docker containers that mount your local MCP server directories as volumes:

```json
{
  "mcpServers": {
    "crypto": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "-v", "C:\\Users\\mac\\Documents\\mcp-server-ccxt-main:/app/mcp-server",
        "crypto-mcp:latest",
        "python",
        "/app/mcp-server/src/server.py"
      ],
      "cwd": "C:\\Users\\mac\\CascadeProjects\\mcp-openai-gemini-llama-example",
      "env": {}
    },
    "binance-futures": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "-v", "C:\\Users\\mac\\Documents\\biance-mcp:/app/binance-mcp",
        "-e", "BINANCE_API_KEY=YOUR_API_KEY_HERE",
        "-e", "BINANCE_SECRET_KEY=YOUR_SECRET_KEY_HERE",
        "-e", "BINANCE_TESTNET=false",
        "binance-futures-mcp:latest",
        "python",
        "/app/binance-mcp/binance-futures-mcp/server.py"
      ],
      "cwd": "C:\\Users\\mac\\CascadeProjects\\mcp-openai-gemini-llama-example",
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Running the Trading Agent

Once the Docker images are built and the configuration is set up, you can run the trading agent:

```bash
py crypto_trading_agent.py
```

## Troubleshooting

If you encounter any issues:

1. Make sure Docker Desktop is running
2. Verify that the paths in the volume mounts match your actual server directories
3. Check that both Docker images were built successfully
4. If you get module import errors, you may need to update the patch file in `docker-patches/mcp_patch.py`

## Benefits of Using Docker

- Consistent Python 3.11 environment for both MCP servers
- Avoids asyncio compatibility issues on Windows
- Isolates dependencies to prevent conflicts
- Makes the setup portable and reproducible
