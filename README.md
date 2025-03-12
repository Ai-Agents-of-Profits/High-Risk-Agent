# Crypto Trading Agent with MCP Servers

This trading agent integrates with your crypto and binance-futures MCP servers to analyze market data and execute trades on Binance Futures.

## Features

- **Market Analysis**: Uses the crypto MCP server tools to analyze market data and identify trading opportunities.
- **Trade Execution**: Places trades on Binance Futures based on analysis.
- **Position Management**: Monitors positions and adjusts stop-losses, takes profits, or exits positions based on changing market conditions.
- **Risk Management**: Implements risk control policies to protect your capital.

## Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure your API Keys**:
   - The Binance API keys should be in your `mcp_config.json` file
   - Set your OpenAI API key as an environment variable:
     ```bash
     set OPENAI_API_KEY=your-key-here
     ```

3. **Run the trading agent**:
   ```bash
   python crypto_trading_agent.py
   ```

## Using the Trading Agent

The agent accepts natural language instructions. Here are some example commands:

- **Market Analysis**:
  - "Analyze the current market conditions for BTC/USDT"
  - "What's the technical analysis for ETH/USDT on the 1-hour timeframe?"
  - "Show me the top 5 coins by volume today"

- **Trade Execution**:
  - "Look for a good entry to go long on BTC/USDT with 2% risk"
  - "Place a short position on ETH/USDT at market price with a stop-loss at $3550"
  - "Set up a limit order to buy BTC/USDT at $60,000 with a stop at $59,000"

- **Position Management**:
  - "Check all my current positions"
  - "Move my stop-loss on BTC/USDT position to breakeven"
  - "Take partial profits (50%) on my ETH/USDT long position"
  - "Close all positions"

- **Order Management**:
  - "Show all my pending orders"
  - "Cancel my limit order for BTC/USDT"

## Architecture

This trading agent uses:
- **MCPClient**: Connects to the MCP servers and provides access to their tools
- **TradingAgent**: Coordinates between market analysis and trade execution
- **OpenAI**: Provides the intelligence layer to interpret data and make decisions (can be replaced with other LLMs)

## Security Note

This agent has access to your Binance account and can place real trades. Always:
1. Start with small position sizes to test
2. Monitor the agent's activities
3. Keep your API keys secure
