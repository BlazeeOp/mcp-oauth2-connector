"""
Security headers middleware.

This module provides middleware for adding comprehensive security headers
to all HTTP responses to protect against various web vulnerabilities.
"""

from fastapi import Request, Response
try:
    from ..utils import get_logger
except ImportError:
    from datakwip_mcp.utils import get_logger


logger = get_logger(__name__)


async def add_security_headers(request: Request, call_next) -> Response:
    """
    Add comprehensive security headers to all responses.
    
    Args:
        request: FastAPI request object
        call_next: Next middleware/endpoint in the chain
        
    Returns:
        Response with security headers added
    """
    # Debug CORS issues
    if request.method == "OPTIONS":
        origin = request.headers.get("origin", "NO_ORIGIN")
        logger.info(f"OPTIONS request from Origin: {origin}, Path: {request.url.path}")
    
    # Process the request through the rest of the application
    response = await call_next(request)
    
    # Add security headers
    security_headers = {
        # Prevent MIME type sniffing
        "X-Content-Type-Options": "nosniff",
        
        # Prevent clickjacking
        "X-Frame-Options": "DENY",
        
        # Enable XSS protection
        "X-XSS-Protection": "1; mode=block",
        
        # Force HTTPS for 1 year
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        
        # Content Security Policy
        "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';",
        
        # Control referrer information
        "Referrer-Policy": "strict-origin-when-cross-origin",
        
        # Disable potentially dangerous browser features
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        
        # Prevent caching of sensitive content
        "Cache-Control": "no-store, no-cache, must-revalidate, private",
        "Pragma": "no-cache",
        "Expires": "0"
    }
    
    # Apply all security headers
    for header_name, header_value in security_headers.items():
        response.headers[header_name] = header_value
    
    # Remove server information for security
    if "server" in response.headers:
        del response.headers["server"]
    
    # Add ngrok skip browser warning header if needed
    response.headers["ngrok-skip-browser-warning"] = "true"
    
    logger.debug(f"Security headers added to response for {request.url.path}")
    
    return response


def get_csp_policy(environment: str = "production") -> str:
    """
    Get Content Security Policy based on environment.
    
    Args:
        environment: Deployment environment (production, development, etc.)
        
    Returns:
        CSP policy string
    """
    if environment == "development":
        # More relaxed CSP for development
        return (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "connect-src 'self' ws: wss:; "
            "img-src 'self' data: https:; "
            "font-src 'self' data: https:;"
        )
    else:
        # Strict CSP for production
        return (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "connect-src 'self' https:; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "object-src 'none'; "
            "media-src 'none'; "
            "frame-src 'none';"
        )