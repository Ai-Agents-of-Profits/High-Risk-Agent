"""
Patch file for MCP server module to add missing functionality required by the Binance Futures MCP server
"""

class InitializationOptions:
    """
    A class to hold initialization options for MCP server.
    This is added to support the Binance Futures MCP server which expects this class.
    """
    def __init__(self, port=None, host=None, server_name=None, stdio=False, custom_model_callbacks=None):
        self.port = port
        self.host = host
        self.server_name = server_name
        self.stdio = stdio
        self.custom_model_callbacks = custom_model_callbacks

# Add the InitializationOptions class to the mcp.server module namespace
import sys
sys.modules['mcp.server'].__dict__['InitializationOptions'] = InitializationOptions
