"""
Configuration settings for the MCP server.

This module handles all environment-based configuration including AWS Cognito,
CORS settings, and client configurations.
"""

import os
from typing import Dict, Any, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_cognito_config() -> Dict[str, Any]:
    """
    Load AWS Cognito configuration from environment variables.
    
    Returns:
        Dict containing Cognito configuration
        
    Raises:
        ValueError: If required environment variables are missing
    """
    required_vars = [
        "COGNITO_USER_POOL_ID",
        "COGNITO_CLIENT_ID", 
        "COGNITO_REGION"
    ]
    
    # Validate all required environment variables exist
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    region = os.getenv("COGNITO_REGION", "us-east-1")
    domain = os.getenv("COGNITO_DOMAIN")
    user_pool_id = os.getenv("COGNITO_USER_POOL_ID")
    
    # Get OAuth scopes from environment (comma-separated)
    scopes_env = os.getenv("COGNITO_OAUTH_SCOPES", "openid,email,profile,aws.cognito.signin.user.admin")
    scopes = [scope.strip() for scope in scopes_env.split(",") if scope.strip()]
    
    # Build default URLs from domain and region
    if domain:
        default_auth_url = f"https://{domain}.auth.{region}.amazoncognito.com/oauth2/authorize"
        default_token_url = f"https://{domain}.auth.{region}.amazoncognito.com/oauth2/token"
    else:
        # Fallback to a generic pattern (user should set COGNITO_DOMAIN)
        default_auth_url = f"https://your-domain.auth.{region}.amazoncognito.com/oauth2/authorize"
        default_token_url = f"https://your-domain.auth.{region}.amazoncognito.com/oauth2/token"
    
    return {
        "user_pool_id": user_pool_id,
        "client_id": os.getenv("COGNITO_CLIENT_ID"),
        "client_secret": os.getenv("COGNITO_CLIENT_SECRET", ""),  # Optional for PKCE flow
        "region": region,
        "domain": domain,
        "scopes": scopes,
        # COGNITO_AUTH_URL and COGNITO_TOKEN_URL are optional overrides
        "authorization_url": os.getenv("COGNITO_AUTH_URL", default_auth_url),
        "token_url": os.getenv("COGNITO_TOKEN_URL", default_token_url),
        "jwks_url": f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json"
    }


def get_cors_config() -> Dict[str, Any]:
    """
    Get secure CORS configuration from environment.
    
    Returns:
        Dict containing CORS configuration
    """
    allowed_origins = os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
    
    # Validate origins - only HTTPS allowed (except localhost in dev)
    valid_origins = []
    for origin in allowed_origins:
        origin = origin.strip()
        if origin and (origin.startswith("https://") or 
                      (origin == "http://localhost" and os.getenv("ENVIRONMENT") == "development")):
            valid_origins.append(origin)
    
    if not valid_origins:
        # Default to specific known clients only
        valid_origins = [
            "https://claude.ai",
            "https://julius.ai", 
            "https://api.julius.ai",
            "https://app.julius.ai"
        ]
        # Add localhost origins for development/testing
    if os.getenv("ENVIRONMENT", "development") == "development":
        valid_origins.extend([
            "http://localhost:6274",
            "http://localhost:3000",
            "http://localhost:8000",
            "http://localhost:8080"
        ])
    
    # Debug logging for CORS origins
    from ..utils import get_logger
    logger = get_logger(__name__)
    logger.info(f"CORS valid_origins: {valid_origins}")
    
    return {
        "allow_origins": valid_origins,
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "OPTIONS"],  # Only required methods
        "allow_headers": ["Authorization", "Content-Type", "MCP-Protocol-Version"],  # Only required headers
        "max_age": 600  # Cache preflight requests for 10 minutes
    }


def get_client_configs() -> Dict[str, Dict[str, Any]]:
    """
    Get client-specific configurations.
    
    Returns:
        Dict containing client configurations
    """
    cognito_config = get_cognito_config()
    
    return {
        "claude": {
            "redirect_uris": ["https://claude.ai/api/mcp/auth_callback"],
            "client_id": os.getenv("CLAUDE_CLIENT_ID", cognito_config["client_id"])
        },
        "julius": {
            "redirect_uris": [
                "https://julius.ai/api/mcp/auth_callback",
                "https://api.julius.ai/mcp/auth_callback",
                "https://app.julius.ai/api/mcp/auth_callback"
            ],
            "client_id": os.getenv("JULIUS_CLIENT_ID", cognito_config["client_id"])
        },
        "default": {
            "redirect_uris": [
                "https://claude.ai/api/mcp/auth_callback",
                "https://julius.ai/api/mcp/auth_callback",
                "https://api.julius.ai/mcp/auth_callback",
                "https://app.julius.ai/api/mcp/auth_callback"
            ],
            "client_id": cognito_config["client_id"]
        }
    }


def get_server_config() -> Dict[str, Any]:
    """
    Get server configuration settings.
    
    Returns:
        Dict containing server configuration
    """
    return {
        "environment": os.getenv("ENVIRONMENT", "development"),
        "base_url": os.getenv("SERVER_BASE_URL", "http://localhost:8000"),
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
        "log_sensitive_data": os.getenv("LOG_SENSITIVE_DATA", "false").lower() == "true"
    }