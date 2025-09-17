"""
DataKwip MCP Connector

A secure Model Context Protocol server with AWS Cognito OAuth2 authentication.
"""

from . import datakwip_mcp

__version__ = "1.0.0"
__author__ = "DataKwip Team"

# Re-export main components for convenience
from .datakwip_mcp.main import app
from .datakwip_mcp.tools import get_tool_registry
from .datakwip_mcp.config import get_cognito_config, get_server_config

__all__ = [
    "app",
    "get_tool_registry", 
    "get_cognito_config",
    "get_server_config"
]