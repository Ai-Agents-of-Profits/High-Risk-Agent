#!/usr/bin/env python3
"""
Crypto Trading Agent

This script connects to both crypto analysis and binance-futures MCP servers
to provide a seamless trading experience that combines market analysis and trade execution.
"""

import os
import sys
import json
import asyncio
import platform
import time
import argparse
import traceback
from typing import Dict, List, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up OpenAI client
from openai import AsyncOpenAI

# Configure OpenAI from environment variables
api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_API_BASE")  # Optional base URL override

# Initialize AsyncOpenAI client with proper configuration
client = AsyncOpenAI(
    api_key=api_key,
    base_url=base_url,  # Will be None if not set in environment
    timeout=60.0,  # Increased timeout to 60 seconds
)

# Constants
MODEL_ID = os.getenv("LLM_MODEL", "gpt-4o")  # Use environment variable with fallback
INITIALIZATION_TIMEOUT = 30  # 30 seconds timeout for server initialization

# MCP imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# System prompt for the trading agent
SYSTEM_PROMPT = """You are a crypto trading assistant that analyzes markets and helps execute trades on Binance Futures.

You have access to two specialized servers:
1. Crypto Market Analysis MCP Server - for analyzing market data, technical indicators, and price patterns
2. Binance Futures Trading MCP Server - for executing trades and managing positions on Binance USDM Futures

Available tools:
{tools}

Current open positions:
{positions}

Pending orders:
{orders}

Please analyze the market data carefully before suggesting any trades. If the user asks you to place a trade:
1. Always check current market conditions using the crypto analysis tools
2. Look at technical indicators, support/resistance levels, and market sentiment
3. Consider risk management - never risk more than 2% of the account on a single trade
4. Provide a clear explanation of your trading rationale
5. Execute trades precisely as described

Remember that you're dealing with real money, so be conservative and prioritize capital preservation.
"""


class MCPClient:
    """
    A client class for interacting with a single MCP server.
    """
    def __init__(self, server_params: StdioServerParameters, server_name: str):
        """Initialize the MCP client with server parameters"""
        self.server_params = server_params
        self.server_name = server_name
        self.session = None
        self._client = None
        self.tools = {}  # Will store available tools

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        try:
            if self.session:
                await self.session.__aexit__(exc_type, exc_val, exc_tb)
        except Exception as e:
            print(f"Error closing session for {self.server_name}: {str(e)}")
            
        try:
            if self._client:
                await self._client.__aexit__(exc_type, exc_val, exc_tb)
        except Exception as e:
            print(f"Error closing client for {self.server_name}: {str(e)}")

    async def connect(self):
        """Establishes connection to MCP server"""
        print(f"Connecting to {self.server_name} MCP server...")
        self._client = stdio_client(self.server_params)
        print(f"DEBUG: Created stdio_client for {self.server_name}")
        self.read, self.write = await self._client.__aenter__()
        print(f"DEBUG: Got read/write streams for {self.server_name}")
        session = ClientSession(self.read, self.write)
        print(f"DEBUG: Created ClientSession for {self.server_name}")
        self.session = await session.__aenter__()
        print(f"DEBUG: Entered session for {self.server_name}")
        
        # Use timeout for initialization to avoid hanging
        try:
            print(f"DEBUG: Starting initialization with {INITIALIZATION_TIMEOUT}s timeout for {self.server_name}")
            initialization_task = asyncio.create_task(self.session.initialize())
            await asyncio.wait_for(initialization_task, timeout=INITIALIZATION_TIMEOUT)
            print(f"DEBUG: Initialized session for {self.server_name}")
            print(f"Connected to {self.server_name} MCP server")
        except asyncio.TimeoutError:
            print(f"ERROR: Timeout while initializing {self.server_name} MCP server after {INITIALIZATION_TIMEOUT} seconds")
            print(f"The server might be stuck waiting for a connection to Binance API.")
            print(f"Will proceed with limited functionality. Some features may not work properly.")
            # We'll continue even with the timeout, as some functionality might still work

    async def get_available_tools(self) -> Dict[str, Any]:
        """
        Retrieve available tools from the MCP server and store them.
        """
        if not self.session:
            raise RuntimeError(f"Not connected to {self.server_name} MCP server")

        try:
            print(f"DEBUG: Getting tools from {self.server_name} MCP server...")
            # Get tool definitions with timeout
            tools_task = asyncio.create_task(self.session.list_tools())
            try:
                tools_response = await asyncio.wait_for(tools_task, timeout=INITIALIZATION_TIMEOUT)
                print(f"DEBUG: Got tools response from {self.server_name}")
                
                # Extract tools from the response
                tools_list = tools_response.tools
                print(f"DEBUG: Extracted {len(tools_list)} tools from {self.server_name}")
                
                # Process tools and store them with callables
                for tool in tools_list:
                    tool_name = tool.name
                    
                    # Create schema dict from tool attributes following the correct format for OpenAI
                    schema = {
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "description": tool.description if hasattr(tool, 'description') else "",
                            "parameters": tool.parameters if hasattr(tool, 'parameters') else {}
                        }
                    }
                    
                    self.tools[tool_name] = {
                        "name": tool_name,
                        "schema": schema,
                        "callable": self.call_tool(tool_name)
                    }
                    
                    # Also store with underscores instead of hyphens for better compatibility
                    alt_name = tool_name.replace("-", "_")
                    if alt_name != tool_name:
                        self.tools[alt_name] = self.tools[tool_name]
                
                print(f"Loaded {len(tools_list)} tools from {self.server_name} MCP server")
                return self.tools
            except asyncio.TimeoutError:
                print(f"ERROR: Timeout getting tools from {self.server_name} after {INITIALIZATION_TIMEOUT} seconds")
                return {}
                
        except Exception as e:
            print(f"Error getting tools from {self.server_name} MCP server: {str(e)}")
            print(f"DEBUG: Full traceback for {self.server_name} tool error:")
            traceback.print_exc()
            return {}

    def call_tool(self, tool_name: str) -> Any:
        """
        Create a callable function for a specific tool.
        
        Args:
            tool_name: The name of the tool to create a callable for

        Returns:
            A callable async function that executes the specified tool
        """
        if not self.session:
            raise RuntimeError(f"Not connected to {self.server_name} MCP server")

        async def callable(*args, **kwargs):
            try:
                # Parameter mapping from OpenAI format to expected server format
                mapped_kwargs = kwargs.copy()
                
                # Special handling for symbol formats in Binance Futures
                if self.server_name == "binance-futures" and "symbol" in mapped_kwargs:
                    # Remove the slash for Binance, which expects BTCUSDT format instead of BTC/USDT
                    mapped_kwargs["symbol"] = mapped_kwargs["symbol"].replace("/", "")
                
                # Convert case for exchange parameter if present
                if "exchange" in mapped_kwargs and isinstance(mapped_kwargs["exchange"], str):
                    mapped_kwargs["exchange"] = mapped_kwargs["exchange"].lower()
                
                print(f"DEBUG: Calling tool {tool_name} with args {mapped_kwargs}")
                
                # Use timeout for tool calls to avoid hanging
                tool_task = asyncio.create_task(self.session.call_tool(tool_name, arguments=mapped_kwargs))
                try:
                    response = await asyncio.wait_for(tool_task, timeout=INITIALIZATION_TIMEOUT)
                    print(f"DEBUG: Got response from tool {tool_name}")
                    
                    # Extract the text content from the response
                    if hasattr(response, 'content') and len(response.content) > 0:
                        result = response.content[0].text
                        print(f"DEBUG: Raw response from {tool_name}: {result[:500]}{'...' if len(result) > 500 else ''}")
                    else:
                        print(f"DEBUG: Empty response from {tool_name}")
                        return {"error": "Empty response"}
                        
                    try:
                        # Try to parse the result as JSON if possible
                        parsed_result = json.loads(result)
                        return parsed_result
                    except:
                        # Return the raw text if it's not valid JSON
                        return result
                except asyncio.TimeoutError:
                    print(f"ERROR: Timeout calling tool {tool_name} after {INITIALIZATION_TIMEOUT} seconds")
                    return {"error": f"Operation timed out after {INITIALIZATION_TIMEOUT} seconds"}
            except Exception as e:
                print(f"Error calling {tool_name}: {str(e)}")
                traceback.print_exc()  # Print the full traceback
                return {"error": str(e)}

        return callable


async def get_market_state(crypto_client, binance_client):
    """
    Get current market state including positions and orders.
    
    Returns:
        Dictionary containing positions and orders
    """
    state = {
        "positions": {},
        "orders": {}
    }
    
    try:
        print("DEBUG: Getting market state...")
        # Get current positions
        positions_tool = binance_client.tools.get("mcp0_get-positions")
        if positions_tool:
            print("DEBUG: Calling get-positions tool")
            try:
                positions = await positions_tool["callable"]()
                print("DEBUG: Got positions response")
                if isinstance(positions, list):
                    state["positions"] = {p.get("symbol", "unknown"): p for p in positions if float(p.get("contracts", 0)) != 0}
            except Exception as e:
                print(f"Error getting positions: {str(e)}")
                state["positions"] = {"error": str(e)}
        
        # Get open orders
        orders_tool = binance_client.tools.get("mcp0_get-open-orders")
        if orders_tool:
            print("DEBUG: Calling get-open-orders tool")
            try:
                orders = await orders_tool["callable"]()
                print("DEBUG: Got orders response")
                if isinstance(orders, list):
                    state["orders"] = {o.get("id", "unknown"): o for o in orders}
            except Exception as e:
                print(f"Error getting orders: {str(e)}")
                state["orders"] = {"error": str(e)}
    except Exception as e:
        print(f"Error getting market state: {str(e)}")
        traceback.print_exc()
    
    return state


async def agent_loop(query: str, crypto_tools: dict, binance_tools: dict, market_state: dict, messages: List[dict] = None):
    """
    Main interaction loop that processes user queries using the LLM and available tools.

    Args:
        query: User's input question or command
        crypto_tools: Dictionary of available crypto analysis tools
        binance_tools: Dictionary of available Binance Futures tools
        market_state: Current market state (positions, orders)
        messages: List of previous messages, defaults to None
    """
    # Combine tools from both MCP servers
    all_tools = {}
    all_tools.update(crypto_tools)
    all_tools.update(binance_tools)
    
    # Initialize messages if not provided
    messages = (
        [
            {
                "role": "system",
                "content": SYSTEM_PROMPT.format(
                    tools="\n- ".join(
                        [
                            f"{t['name']}: {t['schema']['function']['description']}"
                            for t in all_tools.values()
                        ]
                    ),
                    positions=json.dumps(market_state["positions"], indent=2),
                    orders=json.dumps(market_state["orders"], indent=2)
                ),
            },
        ]
        if messages is None
        else messages
    )
    
    # Add user query to messages
    messages.append({"role": "user", "content": query})
    
    try:
        # First response from LLM
        print("Sending request to LLM...")
        first_response = await client.chat.completions.create(
            model=MODEL_ID,
            messages=messages,
            tools=([t["schema"] for t in all_tools.values()] if len(all_tools) > 0 else None),
            temperature=0,
        )
        
        # Check if any tools were called
        stop_reason = (
            "tool_calls"
            if first_response.choices[0].message.tool_calls is not None
            else first_response.choices[0].finish_reason
        )
        
        if stop_reason == "tool_calls":
            # Add the assistant's tool calls to messages
            messages.append(first_response.choices[0].message)
            
            # Process each tool call
            for tool_call in first_response.choices[0].message.tool_calls:
                function_name = tool_call.function.name
                
                # Parse arguments
                try:
                    arguments = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    arguments = {}
                
                print(f"Executing tool: {function_name}")
                
                # Execute the tool if it exists
                if function_name in all_tools:
                    try:
                        tool_result = await all_tools[function_name]["callable"](**arguments)
                        
                        # Add tool result to messages
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": function_name,
                            "content": json.dumps(tool_result),
                        })
                    except Exception as e:
                        error_msg = f"Error executing {function_name}: {str(e)}"
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": function_name,
                            "content": json.dumps({"error": error_msg}),
                        })
                else:
                    # Tool not found
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": json.dumps({"error": f"Tool {function_name} not found"}),
                    })
            
            # Get final response after tool execution
            new_response = await client.chat.completions.create(
                model=MODEL_ID,
                messages=messages,
            )
            
            # Add assistant's response to messages
            messages.append({"role": "assistant", "content": new_response.choices[0].message.content})
            return new_response.choices[0].message.content, messages
        
        elif stop_reason == "stop":
            # If no tools were called, use the first response
            messages.append({"role": "assistant", "content": first_response.choices[0].message.content})
            return first_response.choices[0].message.content, messages
        
        else:
            raise ValueError(f"Unknown stop reason: {stop_reason}")
    
    except Exception as e:
        error_message = f"Error connecting to OpenAI API: {str(e)}"
        print(error_message)
        traceback.print_exc()
        
        # Generate a fallback response without using OpenAI
        fallback_response = "I apologize, but I'm having trouble connecting to my reasoning services. Here's what I can do based on my available tools:\n\n"
        
        # List available tools from both servers
        fallback_response += "From crypto analysis server:\n"
        for tool_name, tool in crypto_tools.items():
            if "schema" in tool and "function" in tool["schema"] and "description" in tool["schema"]["function"]:
                fallback_response += f"- {tool_name}: {tool['schema']['function']['description']}\n"
        
        fallback_response += "\nFrom Binance Futures server:\n"
        for tool_name, tool in binance_tools.items():
            if "schema" in tool and "function" in tool["schema"] and "description" in tool["schema"]["function"]:
                fallback_response += f"- {tool_name}: {tool['schema']['function']['description']}\n"
        
        fallback_response += "\nPlease try a more specific command using one of these tools, or try again later."
        
        # Don't update messages for fallback response
        return fallback_response, messages


async def main():
    """
    Main function that sets up the MCP servers and runs the interactive trading agent.
    """
    start_time = time.time()  # Track execution time
    
    # Check for Windows and set event loop policy if needed
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Load MCP server configurations
    config_path = "mcp_config.json"
    try:
        print(f"Loading configuration from {config_path}...")
        with open(config_path, "r") as f:
            config = json.load(f)
        
        # Configure crypto analysis MCP server
        crypto_config = config["mcpServers"]["crypto"]
        crypto_params = StdioServerParameters(
            command=crypto_config["command"],
            args=crypto_config["args"],
            cwd=crypto_config["cwd"],
            env=crypto_config.get("env", None),
        )
        
        # Configure binance-futures MCP server
        binance_config = config["mcpServers"]["binance-futures"]
        
        # Override environment variables from .env file
        binance_env = binance_config.get("env", {}) if binance_config.get("env") else {}
        # Use mainnet as requested by user
        binance_env["BINANCE_TESTNET"] = "false"
        
        binance_params = StdioServerParameters(
            command=binance_config["command"],
            args=binance_config["args"],
            cwd=binance_config["cwd"],
            env=binance_env,
        )
    except Exception as e:
        print(f"Error loading configuration: {str(e)}")
        traceback.print_exc()
        return
    
    try:
        print("DEBUG: Starting MCP clients...")
        # Start both MCP clients
        async with MCPClient(crypto_params, "crypto") as crypto_client, \
                  MCPClient(binance_params, "binance-futures") as binance_client:
            
            # Get available tools from both servers
            print("DEBUG: Getting crypto tools...")
            crypto_tools = await crypto_client.get_available_tools()
            print("DEBUG: Getting binance tools...")
            binance_tools = await binance_client.get_available_tools()
            
            print(f"Loaded {len(crypto_tools)} tools from crypto server and {len(binance_tools)} tools from binance server")
            
            # Welcome message
            print("\n" + "="*80)
            print("Crypto Trading Agent")
            print("="*80)
            print("Type your instructions for market analysis or trading actions.")
            print("Type 'quit', 'exit', or 'q' to exit the program.")
            print("="*80 + "\n")
            
            # Check if we have tools from both servers
            if len(crypto_tools) == 0:
                print("⚠️ WARNING: No tools loaded from crypto analysis server. Analysis functionality may be limited.")
            
            if len(binance_tools) == 0:
                print("⚠️ WARNING: No tools loaded from binance futures server. Trading functionality may be limited.")
                
            if len(crypto_tools) > 0 and len(binance_tools) > 0:
                print("✅ Both servers connected successfully.")
                
            # Track application startup time
            total_startup_time = time.time() - start_time
            print(f"Startup completed in {total_startup_time:.2f} seconds\n")
            
            # Check OpenAI connectivity
            try:
                test_response = await client.chat.completions.create(
                    model=MODEL_ID,
                    messages=[{"role": "user", "content": "Hello"}],
                    max_tokens=5
                )
                print("✅ OpenAI API connection successful")
            except Exception as e:
                print(f"⚠️ WARNING: Could not connect to OpenAI API: {str(e)}")
                print("Some functionality may be limited. Direct tool calls will still work.")
            
            # Interactive loop
            messages = None
            while True:
                try:
                    # Get user input
                    user_input = input("\nEnter your instruction: ")
                    
                    # Check for exit command
                    if user_input.lower() in ["quit", "exit", "q"]:
                        print("Exiting...")
                        break
                    
                    # Direct tool calls for debugging and when OpenAI is unavailable
                    if user_input.startswith("!tool "):
                        parts = user_input[6:].split(" ", 1)
                        tool_name = parts[0]
                        args_str = parts[1] if len(parts) > 1 else "{}"
                        
                        try:
                            args = json.loads(args_str)
                            print(f"Directly calling tool: {tool_name} with args: {args}")
                            
                            if tool_name in crypto_tools:
                                tool_result = await crypto_tools[tool_name]["callable"](**args)
                                print(f"\nResult: {json.dumps(tool_result, indent=2)}\n")
                            elif tool_name in binance_tools:
                                tool_result = await binance_tools[tool_name]["callable"](**args)
                                print(f"\nResult: {json.dumps(tool_result, indent=2)}\n")
                            else:
                                print(f"Tool {tool_name} not found")
                            continue
                        except Exception as e:
                            print(f"Error calling tool directly: {str(e)}")
                            traceback.print_exc()  # Print the full traceback
                            continue
                    
                    # Log timestamp
                    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Processing...")
                    
                    # Get current market state
                    market_state = await get_market_state(crypto_client, binance_client)
                    
                    # Process query through agent loop
                    response, messages = await agent_loop(
                        user_input, 
                        crypto_tools, 
                        binance_tools, 
                        market_state, 
                        messages
                    )
                    
                    # Print the response
                    print(f"\nResponse: {response}\n")
                    
                except KeyboardInterrupt:
                    print("\nExiting...")
                    break
                except Exception as e:
                    print(f"\nError: {str(e)}")
                    traceback.print_exc()
    
    except Exception as e:
        print(f"Error in main execution: {str(e)}")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
