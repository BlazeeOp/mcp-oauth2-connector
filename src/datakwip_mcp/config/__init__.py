"""Configuration management for the MCP server."""

from .settings import get_cognito_config, get_cors_config, get_client_configs, get_server_config

__all__ = [
    "get_cognito_config",
    "get_cors_config", 
    "get_client_configs",
    "get_server_config"
]