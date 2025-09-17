"""
Error handling utilities.

This module provides centralized error handling with secure error messaging
that prevents information disclosure while maintaining debugging capability.
"""

import secrets
import logging
from typing import Dict, Any, Optional
from fastapi import HTTPException
import jwt


class SecureErrorHandler:
    """
    Centralized secure error handling that provides safe user messages
    while logging detailed information for debugging.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the error handler.
        
        Args:
            logger: Logger instance for internal error logging
        """
        self.logger = logger or logging.getLogger(__name__)
    
    def get_safe_error_message(self, exception: Exception, request_id: str = None) -> Dict[str, Any]:
        """
        Convert an exception to a safe error message for user consumption.
        
        Args:
            exception: The exception that occurred
            request_id: Optional request ID for tracking
            
        Returns:
            Dict containing safe error message and metadata
        """
        if not request_id:
            request_id = secrets.token_hex(8)
        
        # Log full error internally with request ID for debugging
        self.logger.error(
            f"Error ID {request_id}: {type(exception).__name__}: {str(exception)}"
        )
        
        # Map exceptions to safe user messages
        error_mapping = {
            jwt.ExpiredSignatureError: ("Token has expired", 401),
            jwt.InvalidTokenError: ("Invalid authentication token", 401),
            jwt.DecodeError: ("Invalid authentication token", 401),
            ValueError: ("Invalid request data", 400),
            KeyError: ("Missing required data", 400),
            TypeError: ("Invalid data type", 400),
        }
        
        # Handle HTTPException specially to preserve status codes
        if isinstance(exception, HTTPException):
            message = exception.detail if hasattr(exception, 'detail') else "Request failed"
            status_code = exception.status_code if hasattr(exception, 'status_code') else 400
        else:
            # Get mapped message or use default
            message, status_code = error_mapping.get(
                type(exception),
                ("An error occurred processing your request", 500)
            )
        
        return {
            "error": message,
            "error_id": request_id,
            "status_code": status_code
        }
    
    def create_http_exception(self, exception: Exception, request_id: str = None) -> HTTPException:
        """
        Create an HTTPException with safe error messaging.
        
        Args:
            exception: The original exception
            request_id: Optional request ID for tracking
            
        Returns:
            HTTPException with safe error message
        """
        error_info = self.get_safe_error_message(exception, request_id)
        
        return HTTPException(
            status_code=error_info["status_code"],
            detail={
                "error": error_info["error"],
                "error_id": error_info["error_id"]
            }
        )


class MCPError(Exception):
    """Base exception for MCP-specific errors."""
    
    def __init__(self, code: int, message: str, data: Any = None):
        """
        Initialize MCP error.
        
        Args:
            code: MCP error code
            message: Error message
            data: Additional error data
        """
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


class AuthenticationError(MCPError):
    """Authentication-related errors."""
    
    def __init__(self, message: str = "Authentication failed", data: Any = None):
        super().__init__(-32001, message, data)


class AuthorizationError(MCPError):
    """Authorization-related errors."""
    
    def __init__(self, message: str = "Insufficient permissions", data: Any = None):
        super().__init__(-32002, message, data)


class ValidationError(MCPError):
    """Input validation errors."""
    
    def __init__(self, message: str = "Invalid input", data: Any = None):
        super().__init__(-32003, message, data)


class RateLimitError(MCPError):
    """Rate limiting errors."""
    
    def __init__(self, message: str = "Rate limit exceeded", data: Any = None):
        super().__init__(-32004, message, data)