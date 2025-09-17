"""
Input validation utilities.

This module provides functions for validating various inputs including JWT tokens,
user data, and request parameters.
"""

import re
from typing import Any


def validate_jwt_token_format(token: str) -> bool:
    """
    Validate JWT token format before processing.
    
    Args:
        token: JWT token string to validate
        
    Returns:
        True if token format is valid, False otherwise
    """
    # Basic JWT format validation (3 parts separated by dots)
    parts = token.split(".")
    if len(parts) != 3:
        return False
    
    # Check each part is valid base64url
    base64url_pattern = re.compile(r'^[A-Za-z0-9_-]+$')
    for part in parts:
        if not base64url_pattern.match(part):
            return False
    
    # Limit token size (prevent DoS)
    if len(token) > 10000:  # Reasonable max size for JWT
        return False
    
    return True


def validate_mcp_method(method: str) -> bool:
    """
    Validate MCP method name.
    
    Args:
        method: MCP method name to validate
        
    Returns:
        True if method is valid, False otherwise
    """
    if not method or not isinstance(method, str):
        return False
    
    # Limit method name length
    if len(method) > 100:
        return False
    
    # Check for valid MCP method patterns
    valid_patterns = [
        r'^initialize$',
        r'^notifications/initialized$',
        r'^tools/list$',
        r'^tools/call$',
        r'^prompts/list$',
        r'^prompts/get$',
        r'^resources/list$',
        r'^resources/read$'
    ]
    
    return any(re.match(pattern, method) for pattern in valid_patterns)


def sanitize_string_input(input_str: str, max_length: int = 1000) -> str:
    """
    Sanitize string input by removing control characters and limiting length.
    
    Args:
        input_str: String to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
    """
    if not isinstance(input_str, str):
        return ""
    
    # Limit length
    sanitized = input_str[:max_length]
    
    # Remove control characters
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', sanitized)
    
    return sanitized.strip()