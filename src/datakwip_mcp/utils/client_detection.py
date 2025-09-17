"""
Client detection utilities.

This module provides secure client detection based on HTTP headers
with proper input validation and sanitization.
"""

import re
from fastapi import Request
from typing import Dict, List


def detect_client_securely(request: Request) -> str:
    """
    Securely detect client type with input validation.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Detected client type or "unknown"
    """
    # Validate and sanitize headers with length limits
    user_agent = request.headers.get("user-agent", "")[:500].lower()
    referer = request.headers.get("referer", "")[:500].lower() 
    origin = request.headers.get("origin", "")[:500].lower()
    
    # Remove any control characters for security
    sanitize = lambda s: re.sub(r'[\x00-\x1f\x7f-\x9f]', '', s)
    user_agent = sanitize(user_agent)
    referer = sanitize(referer)
    origin = sanitize(origin)
    
    # Whitelist-based client detection patterns
    client_patterns = {
        "julius": ["julius.ai", "api.julius.ai", "app.julius.ai"],
        "claude": ["claude.ai", "anthropic"]
    }
    
    # Check each client pattern against headers
    for client, patterns in client_patterns.items():
        for pattern in patterns:
            if any(pattern in src for src in [user_agent, referer, origin]):
                return client
    
    return "unknown"


def validate_client_type(client_type: str) -> bool:
    """
    Validate that a client type is in the allowed list.
    
    Args:
        client_type: Client type string to validate
        
    Returns:
        True if client type is valid, False otherwise
    """
    allowed_clients = {"julius", "claude", "unknown", "default"}
    return client_type in allowed_clients


def get_client_info(client_type: str) -> Dict[str, str]:
    """
    Get display information for a client type.
    
    Args:
        client_type: Client type identifier
        
    Returns:
        Dict containing client display information
    """
    client_info = {
        "julius": {
            "name": "Julius AI",
            "description": "Julius AI Platform"
        },
        "claude": {
            "name": "Claude AI",
            "description": "Anthropic Claude AI Assistant"
        },
        "unknown": {
            "name": "Unknown Client",
            "description": "Unidentified client application"
        }
    }
    
    return client_info.get(client_type, client_info["unknown"])