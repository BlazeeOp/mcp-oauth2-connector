"""
AWS Cognito authentication module.

This module handles JWT token validation with AWS Cognito including
comprehensive security checks and proper error handling.
"""

import jwt
import json
import httpx
import time
from typing import Dict, Any, Optional, List
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt.algorithms import RSAAlgorithm

try:
    from ..config import get_cognito_config
    from ..utils import validate_jwt_token_format, get_logger, SecureErrorHandler
except ImportError:
    from datakwip_mcp.config import get_cognito_config
    from datakwip_mcp.utils import validate_jwt_token_format, get_logger, SecureErrorHandler


# Initialize components
logger = get_logger(__name__)
security = HTTPBearer(auto_error=False)
error_handler = SecureErrorHandler(logger)


async def validate_cognito_token(
    token: str,
    cognito_config: Optional[Dict[str, Any]] = None,
    required_scopes: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Securely validate AWS Cognito JWT token with comprehensive security checks.
    
    Args:
        token: JWT token to validate
        cognito_config: Optional Cognito configuration (uses default if None)
        required_scopes: Optional list of required scopes for access tokens
        
    Returns:
        Validated token payload
        
    Raises:
        jwt.InvalidTokenError: If token validation fails
        jwt.ExpiredSignatureError: If token has expired
    """
    if cognito_config is None:
        cognito_config = get_cognito_config()
    
    # Validate token format first
    if not validate_jwt_token_format(token):
        logger.warning("Invalid JWT token format received")
        raise jwt.InvalidTokenError("Invalid token format")
    
    # Set up HTTP client with timeout
    timeout = httpx.Timeout(10.0, connect=5.0)
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            # Validate JWKS URL is from AWS (security check)
            jwks_url = cognito_config["jwks_url"]
            if not jwks_url.startswith("https://cognito-idp.") or ".amazonaws.com" not in jwks_url:
                logger.error(f"Invalid JWKS URL: {jwks_url}")
                raise ValueError("Invalid JWKS URL")
            
            # Fetch JWKS
            logger.debug(f"Fetching JWKS from: {jwks_url}")
            jwks_response = await client.get(jwks_url)
            jwks_response.raise_for_status()
            jwks = jwks_response.json()
    
    except httpx.TimeoutException:
        logger.error("JWKS fetch timeout")
        raise jwt.InvalidTokenError("Token validation timeout")
    except httpx.HTTPStatusError as e:
        logger.error(f"JWKS fetch failed: {e}")
        raise jwt.InvalidTokenError("Unable to fetch JWKS")
    except Exception as e:
        logger.error(f"JWKS fetch error: {e}")
        raise jwt.InvalidTokenError("JWKS validation failed")
    
    # Get token header and find matching key
    try:
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        
        if not kid:
            logger.warning("Token missing key ID")
            raise jwt.InvalidTokenError("Token missing key ID")
        
        # Find matching RSA key
        rsa_key = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                logger.debug(f"Found matching key with kid: {kid}")
                rsa_key = RSAAlgorithm.from_jwk(json.dumps(key))
                break
        
        if not rsa_key:
            logger.warning(f"No matching key found for kid: {kid}")
            raise jwt.InvalidTokenError("Unable to find appropriate key")
    
    except Exception as e:
        logger.error(f"Key resolution failed: {e}")
        raise jwt.InvalidTokenError("Key resolution failed")
    
    # Decode and validate token
    issuer = f"https://cognito-idp.{cognito_config['region']}.amazonaws.com/{cognito_config['user_pool_id']}"
    
    try:
        # First decode without audience validation to check if aud claim exists
        payload_check = jwt.decode(token, options={"verify_signature": False})
        has_audience = "aud" in payload_check
        
        # Decode with appropriate validation options
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            issuer=issuer,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iat": True,
                "verify_aud": has_audience
            },
            audience=cognito_config.get("client_id") if has_audience else None
        )
    
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        raise
    except jwt.InvalidTokenError as e:
        logger.warning(f"Token validation failed: {str(e)}")
        raise jwt.InvalidTokenError(f"Token validation failed: {str(e)}")
    
    # Additional security checks
    try:
        # 1. Validate token use
        token_use = payload.get("token_use")
        if token_use not in ["id", "access"]:
            logger.warning(f"Invalid token use: {token_use}")
            raise jwt.InvalidTokenError("Invalid token use")
        
        # 2. Check required scopes if specified
        if required_scopes and token_use == "access":
            token_scopes = payload.get("scope", "").split()
            missing_scopes = [scope for scope in required_scopes if scope not in token_scopes]
            if missing_scopes:
                logger.warning(f"Missing required scopes: {missing_scopes}")
                raise jwt.InvalidTokenError("Insufficient token scopes")
        
        # 3. Validate subject exists
        if not payload.get("sub"):
            logger.warning("Token missing subject")
            raise jwt.InvalidTokenError("Token missing subject")
        
        # 4. Check token age (prevent old token reuse)
        iat = payload.get("iat", 0)
        current_time = time.time()
        max_age = 3600 * 24  # 24 hours
        if current_time - iat > max_age:
            logger.warning(f"Token too old: {current_time - iat} seconds")
            raise jwt.InvalidTokenError("Token too old")
        
        # Log successful validation
        user_identifier = payload.get('email') or payload.get('username') or payload.get('sub', 'unknown')
        logger.info(f"Token validation successful for user: {user_identifier}")
        
        return payload
    
    except Exception as e:
        logger.error(f"Token security validation failed: {e}")
        raise jwt.InvalidTokenError(f"Token security validation failed")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security), 
    request: Request = None
) -> Dict[str, Any]:
    """
    Extract and validate user from authorization header.
    
    Args:
        credentials: HTTP authorization credentials
        request: FastAPI request object
        
    Returns:
        Validated user information from token
        
    Raises:
        HTTPException: If authentication fails
    """
    logger.debug("Starting authentication check")
    
    if not credentials:
        logger.warning("No authorization credentials provided")
        base_url = request.base_url if request else "https://localhost:8000"
        raise HTTPException(
            status_code=401,
            detail="Authorization header required",
            headers={
                "WWW-Authenticate": f'Bearer resource_metadata="{base_url}/.well-known/oauth-protected-resource"'
            }
        )
    
    token = credentials.credentials
    logger.debug(f"Processing token: {token[:20]}...")
    
    try:
        user_info = await validate_cognito_token(token)
        user_id = user_info.get('username') or user_info.get('sub', 'unknown')
        logger.info(f"User authenticated: {user_id}")
        return user_info
    
    except jwt.ExpiredSignatureError:
        logger.warning("Authentication failed: Token expired")
        raise error_handler.create_http_exception(
            jwt.ExpiredSignatureError("Token has expired")
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Authentication failed: {str(e)}")
        raise error_handler.create_http_exception(e)
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise error_handler.create_http_exception(e)