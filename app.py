from flask import Flask, render_template, request, jsonify
import asyncio
import json
import os
import time
import sys
import platform
from dotenv import load_dotenv
from openai import OpenAI
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from concurrent.futures import ThreadPoolExecutor

# Import from the crypto trading agent
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from crypto_trading_agent import (
    get_market_state,
    agent_loop,
    MCPClient,
    MODEL_ID as LLM_MODEL
)

load_dotenv()

app = Flask(__name__)

# Global variables
config = None
crypto_client = None
binance_client = None
crypto_tools = {}
binance_tools = {}
client = None
market_state = {}
loop = None
executor = ThreadPoolExecutor(max_workers=2)

@app.route('/')
def index():
    return render_template('index.html')

def run_async(coro):
    """Helper function to run async code from sync context"""
    return asyncio.run_coroutine_threadsafe(coro, loop).result()

@app.route('/api/prompt', methods=['POST'])
def handle_prompt():
    global market_state
    data = request.json
    user_input = data.get('prompt')
    
    if not user_input:
        return jsonify({"error": "No prompt provided"}), 400
    
    try:
        # Process the user instruction in a thread-safe way
        start_time = time.time()
        
        # First refresh market state
        market_state = run_async(get_market_state(crypto_client, binance_client))
        
        # Create a temporary copy of the state and tools for the agent
        async def process():
            return await agent_loop(user_input, crypto_tools, binance_tools, market_state)
            
        # Run the agent loop in the event loop
        result = run_async(process())
        
        processing_time = time.time() - start_time
        
        # agent_loop returns a tuple of (response_text, messages)
        # We only want to return the first element (response_text)
        if isinstance(result, tuple) and len(result) > 0:
            response_text = result[0]
        else:
            response_text = str(result)
        
        # Check if response_text is a ChatCompletionMessage and extract content if needed
        if hasattr(response_text, 'content'):
            response_text = response_text.content
        
        return jsonify({
            "response": response_text,
            "processing_time": f"{processing_time:.2f}"
        })
    except Exception as e:
        print(f"Error processing prompt: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/status')
def get_status():
    try:
        status = {
            "crypto_connected": crypto_client is not None and crypto_client.session is not None,
            "binance_connected": binance_client is not None and binance_client.session is not None,
            "openai_connected": client is not None,
            "crypto_tools_count": len(crypto_tools) if crypto_tools else 0,
            "binance_tools_count": len(binance_tools) if binance_tools else 0,
            "llm_model": LLM_MODEL
        }
        return jsonify(status)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

async def load_mcp_config():
    """Load the MCP server configuration from mcp_config.json"""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_config.json")
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading MCP config: {e}")
        return {"mcpServers": {}}

async def initialize_clients():
    global config, crypto_client, binance_client, crypto_tools, binance_tools, client, market_state
    
    print("Loading configuration from mcp_config.json...")
    config = await load_mcp_config()
    
    print("Starting MCP clients...")
    
    # Initialize MCP clients
    if "crypto" in config.get("mcpServers", {}):
        crypto_server_params = StdioServerParameters(
            command=config["mcpServers"]["crypto"]["command"],
            args=config["mcpServers"]["crypto"]["args"],
            cwd=config["mcpServers"]["crypto"]["cwd"],
            env=config["mcpServers"]["crypto"].get("env", {})
        )
        crypto_client = MCPClient(crypto_server_params, "crypto")
        await crypto_client.connect()
        print("Connected to crypto MCP server")
        crypto_tools = await crypto_client.get_available_tools()
        print(f"Loaded {len(crypto_tools)} tools from crypto MCP server")
    
    if "binance-futures" in config.get("mcpServers", {}):
        binance_server_params = StdioServerParameters(
            command=config["mcpServers"]["binance-futures"]["command"],
            args=config["mcpServers"]["binance-futures"]["args"],
            cwd=config["mcpServers"]["binance-futures"]["cwd"],
            env=config["mcpServers"]["binance-futures"].get("env", {})
        )
        binance_client = MCPClient(binance_server_params, "binance-futures")
        await binance_client.connect()
        print("Connected to binance-futures MCP server")
        binance_tools = await binance_client.get_available_tools()
        print(f"Loaded {len(binance_tools)} tools from binance-futures MCP server")
    
    # Initialize OpenAI client
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Get initial market state
    market_state = await get_market_state(crypto_client, binance_client)
    
    print("\n✅ Initialization complete")
    print(f"Loaded {len(crypto_tools)} tools from crypto server and {len(binance_tools)} tools from binance server")

def start_background_loop(loop):
    """Set event loop in the current thread and run it forever"""
    asyncio.set_event_loop(loop)
    loop.run_forever()

if __name__ == '__main__':
    # Create a new event loop for async operations
    loop = asyncio.new_event_loop()
    
    # Start the loop in a background thread
    import threading
    t = threading.Thread(target=start_background_loop, args=(loop,))
    t.daemon = True
    t.start()
    
    # Initialize clients in the background loop
    future = asyncio.run_coroutine_threadsafe(initialize_clients(), loop)
    future.result()  # Wait for initialization to complete
    
    # Run Flask app in the main thread
    app.run(debug=True, port=5000, use_reloader=False)
