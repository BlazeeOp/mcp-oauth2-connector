"""
OAuth2 endpoint handlers.

This module provides OAuth2 discovery endpoints and dynamic client registration
following OAuth2 and OpenID Connect specifications.
"""

import json
from typing import Dict, Any, List
from fastapi import Request, HTTPException

try:
    from ..config import get_cognito_config, get_client_configs
    from ..utils import get_logger, detect_client_securely, sanitize_log_output
except ImportError:
    from datakwip_mcp.config import get_cognito_config, get_client_configs
    from datakwip_mcp.utils import get_logger, detect_client_securely, sanitize_log_output


logger = get_logger(__name__)


def create_resource_metadata() -> Dict[str, Any]:
    """
    Create OAuth2 Protected Resource metadata.
    
    Returns:
        Dict containing OAuth2 protected resource metadata
    """
    cognito_config = get_cognito_config()
    
    return {
        "resource": "mcp-server",
        "authorization_servers": [
            f"https://cognito-idp.{cognito_config['region']}.amazonaws.com/{cognito_config['user_pool_id']}"
        ],
        "scopes_supported": cognito_config["scopes"],
        "bearer_methods_supported": ["header"],
        "resource_documentation": "MCP Server with AWS Cognito OAuth2"
    }


async def oauth_authorization_server(request: Request) -> Dict[str, Any]:
    """
    OAuth2 Authorization Server metadata endpoint.
    
    Args:
        request: FastAPI request object
        
    Returns:
        OAuth2 authorization server metadata
    """
    logger.info("Returning OAuth2 Authorization Server metadata")
    
    # Get configuration
    cognito_config = get_cognito_config()
    base_url = f"{request.url.scheme}://{request.url.netloc}"
    
    # Build Cognito base URL using configured domain and region
    if cognito_config.get('domain'):
        cognito_base_url = f"https://{cognito_config['domain']}.auth.{cognito_config['region']}.amazoncognito.com"
    else:
        # Fallback for when domain is not configured
        cognito_base_url = f"https://your-domain.auth.{cognito_config['region']}.amazoncognito.com"
    
    # Create metadata following OAuth2 specification
    metadata = {
        "issuer": f"https://cognito-idp.{cognito_config['region']}.amazonaws.com/{cognito_config['user_pool_id']}",
        "authorization_endpoint": cognito_config["authorization_url"],
        "token_endpoint": cognito_config["token_url"],
        "registration_endpoint": f"{base_url}/register",  # Point to our app's register endpoint
        "jwks_uri": cognito_config["jwks_url"],
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "token_endpoint_auth_methods_supported": ["none"],  # PKCE
        "scopes_supported": cognito_config["scopes"],
        "code_challenge_methods_supported": ["S256"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["RS256"]
    }
    
    logger.debug(f"OAuth2 metadata: {sanitize_log_output(str(metadata))}")
    return metadata


async def oauth_protected_resource() -> Dict[str, Any]:
    """
    OAuth2 Protected Resource metadata endpoint.
    
    Returns:
        OAuth2 protected resource metadata
    """
    logger.debug("Returning OAuth2 Protected Resource metadata")
    return create_resource_metadata()


async def oauth_protected_resource_mcp() -> Dict[str, Any]:
    """
    OAuth2 Protected Resource MCP-specific metadata endpoint.
    
    Returns:
        OAuth2 protected resource metadata (same as parent endpoint)
    """
    logger.info("OAuth Protected Resource MCP endpoint accessed")
    return create_resource_metadata()


async def oauth_authorization_server_mcp(request: Request) -> Dict[str, Any]:
    """
    OAuth2 Authorization Server MCP-specific metadata endpoint.
    
    Args:
        request: FastAPI request object
        
    Returns:
        OAuth2 authorization server metadata (same as parent endpoint)
    """
    logger.info("OAuth Authorization Server MCP endpoint accessed")
    return await oauth_authorization_server(request)


async def dynamic_client_registration(request: Request) -> Dict[str, Any]:
    """
    Dynamic Client Registration endpoint (DCR).
    
    Args:
        request: FastAPI request object
        
    Returns:
        Client registration information
    """
    # Get request body for analysis
    try:
        body = await request.body()
        logger.info(f"DCR request received from {request.client.host if request.client else 'unknown'}")
        
        # Detect which client is registering
        client_type = detect_client_securely(request)
        logger.info(f"Detected client type: {client_type}")
        
        # Parse request body to check for redirect_uris
        request_data = {}
        if body:
            try:
                request_data = json.loads(body)
                requested_redirect_uris = request_data.get("redirect_uris", [])
                
                # Refine client detection based on redirect URIs
                if requested_redirect_uris:
                    for uri in requested_redirect_uris:
                        uri_lower = uri.lower()
                        if "julius" in uri_lower:
                            client_type = "julius"
                            break
                        elif "claude" in uri_lower:
                            client_type = "claude"
                            break
            except json.JSONDecodeError:
                logger.warning("Invalid JSON in DCR request body")
        
        # Get client and cognito configurations
        client_configs = get_client_configs()
        client_config = client_configs.get(client_type, client_configs["default"])
        cognito_config = get_cognito_config()
        
        # Create client registration response
        client_info = {
            "client_id": client_config["client_id"],
            "client_secret": cognito_config["client_secret"],  # From environment variable
            "client_id_issued_at": 1640995200,  # Static timestamp
            "redirect_uris": client_config["redirect_uris"],
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none" if not cognito_config["client_secret"] else "client_secret_basic",
            "scope": " ".join(cognito_config["scopes"])
        }
        
        logger.info(f"DCR response for {client_type}: client_id={client_info['client_id']}")
        return client_info
        
    except Exception as e:
        logger.error(f"DCR request processing failed: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail="Invalid client registration request"
        )


def get_oauth_endpoints() -> List[Dict[str, Any]]:
    """
    Get list of OAuth2 endpoint configurations for FastAPI router registration.
    
    Returns:
        List of endpoint configurations
    """
    return [
        {
            "path": "/.well-known/oauth-authorization-server",
            "method": "GET",
            "handler": oauth_authorization_server,
            "name": "oauth_authorization_server"
        },
        {
            "path": "/.well-known/oauth-protected-resource",
            "method": "GET", 
            "handler": oauth_protected_resource,
            "name": "oauth_protected_resource"
        },
        {
            "path": "/.well-known/oauth-protected-resource/mcp",
            "method": "GET",
            "handler": oauth_protected_resource_mcp,
            "name": "oauth_protected_resource_mcp"
        },
        {
            "path": "/.well-known/oauth-authorization-server/mcp",
            "method": "GET",
            "handler": oauth_authorization_server_mcp,
            "name": "oauth_authorization_server_mcp"
        },
        {
            "path": "/register",
            "method": "POST",
            "handler": dynamic_client_registration,
            "name": "dynamic_client_registration"
        }
    ]