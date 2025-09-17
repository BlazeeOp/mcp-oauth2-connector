#!/usr/bin/env python3
"""
Command Line Interface for DataKwip MCP Server

This module provides CLI commands for running and managing the MCP server.
"""

import sys
import argparse
import uvicorn
from typing import Optional

try:
    from .main import app
    from .config import get_server_config
    from .utils import get_logger
except ImportError:
    from datakwip_mcp.main import app
    from datakwip_mcp.config import get_server_config
    from datakwip_mcp.utils import get_logger


logger = get_logger(__name__)


def run_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    reload: Optional[bool] = None,
    log_level: Optional[str] = None
):
    """
    Run the DataKwip MCP server.
    
    Args:
        host: Host to bind to (default: 0.0.0.0)
        port: Port to bind to (default: 8000)
        reload: Enable auto-reload (default: based on environment)
        log_level: Logging level (default: from config)
    """
    try:
        # Load server configuration
        server_config = get_server_config()
        
        # Use provided values or fall back to config
        if reload is None:
            reload = server_config["environment"] == "development"
        
        if log_level is None:
            log_level = server_config["log_level"].lower()
        
        logger.info(f"Starting DataKwip MCP Server on {host}:{port}")
        logger.info(f"Environment: {server_config['environment']}")
        logger.info(f"Reload: {reload}")
        
        # Run the server
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level=log_level,
            reload=reload
        )
        
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="DataKwip MCP Server - Secure Model Context Protocol server with AWS Cognito OAuth2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  datakwip-mcp                          # Run server with default settings
  datakwip-mcp --port 8080              # Run on port 8080
  datakwip-mcp --host 127.0.0.1 --dev   # Run in development mode on localhost
  datakwip-mcp --reload --log-level debug  # Run with auto-reload and debug logging
        """
    )
    
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)"
    )
    
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )
    
    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="Disable auto-reload"
    )
    
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Enable development mode (auto-reload, debug logging)"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Set logging level"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="DataKwip MCP Server 1.0.0"
    )
    
    args = parser.parse_args()
    
    # Determine reload setting
    reload = None
    if args.dev:
        reload = True
        if args.log_level is None:
            args.log_level = "debug"
    elif args.reload:
        reload = True
    elif args.no_reload:
        reload = False
    
    # Run the server
    run_server(
        host=args.host,
        port=args.port,
        reload=reload,
        log_level=args.log_level
    )


if __name__ == "__main__":
    main()