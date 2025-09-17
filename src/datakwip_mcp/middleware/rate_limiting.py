"""
Rate limiting middleware and configuration.

This module provides rate limiting setup using SlowAPI with configurable
limits and proper error handling.
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import FastAPI

try:
    from ..utils import get_logger
except ImportError:
    from datakwip_mcp.utils import get_logger


logger = get_logger(__name__)


def get_real_client_ip(request):
    """
    Get the real client IP considering proxies and load balancers.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Client IP address string
    """
    # Check for X-Forwarded-For header (common with proxies)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # Take the first IP in the chain (original client)
        client_ip = forwarded_for.split(",")[0].strip()
        logger.debug(f"Using X-Forwarded-For IP: {client_ip}")
        return client_ip
    
    # Check for X-Real-IP header (nginx)
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        logger.debug(f"Using X-Real-IP: {real_ip}")
        return real_ip
    
    # Fall back to direct connection IP
    client_ip = get_remote_address(request)
    logger.debug(f"Using direct IP: {client_ip}")
    return client_ip


def setup_rate_limiting(app: FastAPI) -> Limiter:
    """
    Set up rate limiting for the FastAPI application.
    
    Args:
        app: FastAPI application instance
        
    Returns:
        Configured Limiter instance
    """
    # Create limiter with custom key function
    limiter = Limiter(
        key_func=get_real_client_ip,
        default_limits=["100 per minute", "1000 per hour"]
    )
    
    # Add limiter to app state
    app.state.limiter = limiter
    
    # Add exception handler for rate limit exceeded
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    logger.info("Rate limiting configured with default limits: 100/min, 1000/hour")
    
    return limiter


def get_endpoint_rate_limits() -> dict:
    """
    Get rate limit configurations for different endpoint types.
    
    Returns:
        Dict mapping endpoint types to rate limit strings
    """
    return {
        # OAuth and auth endpoints - more restrictive
        "oauth": "10 per minute",
        "auth": "10 per minute",
        "register": "5 per minute",
        
        # MCP endpoints - moderate limits
        "mcp_metadata": "20 per minute",
        "mcp_handler": "30 per minute",
        "tools": "50 per minute",
        
        # Utility endpoints - generous limits
        "health": "100 per minute",
        "debug": "10 per minute",
        
        # Test endpoints - restrictive for security
        "test": "5 per minute"
    }


class RateLimitConfig:
    """Configuration class for rate limiting settings."""
    
    # OAuth endpoints
    OAUTH_LIMIT = "10 per minute"
    REGISTER_LIMIT = "5 per minute"
    
    # MCP endpoints  
    MCP_METADATA_LIMIT = "20 per minute"
    MCP_HANDLER_LIMIT = "30 per minute"
    
    # Utility endpoints
    HEALTH_LIMIT = "100 per minute"
    DEBUG_LIMIT = "10 per minute"
    
    # Test endpoints
    TEST_LIMIT = "5 per minute"
    
    # Global defaults
    DEFAULT_PER_MINUTE = "100 per minute"
    DEFAULT_PER_HOUR = "1000 per hour"