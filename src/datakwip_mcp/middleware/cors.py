"""
CORS middleware configuration.

This module provides secure CORS configuration with proper origin validation
and restrictive settings for production environments.
"""

from fastapi.middleware.cors import CORSMiddleware
try:
    from ..config import get_cors_config
    from ..utils import get_logger
except ImportError:
    from datakwip_mcp.config import get_cors_config
    from datakwip_mcp.utils import get_logger


logger = get_logger(__name__)


def get_cors_middleware() -> tuple:
    """
    Get configured CORS middleware with secure settings.
    
    Returns:
        Tuple of (CORSMiddleware class, configuration dict)
    """
    cors_config = get_cors_config()
    
    logger.info(f"CORS configured with {len(cors_config['allow_origins'])} allowed origins")
    logger.debug(f"Allowed origins: {cors_config['allow_origins']}")
    
    return CORSMiddleware, cors_config


def validate_cors_origin(origin: str, allowed_origins: list) -> bool:
    """
    Validate if an origin is allowed for CORS requests.
    
    Args:
        origin: Origin header value from request
        allowed_origins: List of allowed origins
        
    Returns:
        True if origin is allowed, False otherwise
    """
    if not origin:
        return False
    
    # Check exact matches
    if origin in allowed_origins:
        return True
    
    # Check for wildcard patterns (if any are configured)
    for allowed in allowed_origins:
        if allowed == "*":
            logger.warning("Wildcard CORS origin detected - security risk!")
            return True
        # Could add subdomain matching logic here if needed
    
    logger.warning(f"CORS request from unauthorized origin: {origin}")
    return False