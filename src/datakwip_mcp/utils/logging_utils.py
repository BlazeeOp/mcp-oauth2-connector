"""
Logging utilities for secure logging.

This module provides utilities for secure logging, preventing sensitive data exposure
and log injection attacks.
"""

import logging
import re
import os
from typing import Any


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        # Configure logging if not already configured
        log_level = os.getenv("LOG_LEVEL", "INFO")
        
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    return logger


def sanitize_log_output(data: Any, max_length: int = 100) -> str:
    """
    Sanitize data for logging to prevent injection attacks and limit exposure.
    
    Args:
        data: Data to sanitize for logging
        max_length: Maximum length for the sanitized string
        
    Returns:
        Sanitized string safe for logging
    """
    if data is None:
        return "None"
    
    # Convert to string and limit length
    str_data = str(data)[:max_length]
    
    # Remove control characters and newlines to prevent log injection
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f\r\n]', ' ', str_data)
    
    # Check if we should log sensitive data
    log_sensitive = os.getenv("LOG_SENSITIVE_DATA", "false").lower() == "true"
    
    if not log_sensitive:
        # Mask potential sensitive data patterns
        # JWT tokens
        sanitized = re.sub(r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', '[JWT_TOKEN]', sanitized)
        # Email addresses
        sanitized = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', sanitized)
        # Phone numbers
        sanitized = re.sub(r'\b\d{3}-?\d{3}-?\d{4}\b', '[PHONE]', sanitized)
        # Credit card numbers (basic pattern)
        sanitized = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CARD]', sanitized)
    
    return sanitized


def log_request_info(logger: logging.Logger, request_id: str, method: str, 
                    user_id: str = None, client_type: str = None) -> None:
    """
    Log standardized request information.
    
    Args:
        logger: Logger instance
        request_id: Unique request identifier
        method: HTTP/MCP method
        user_id: User identifier (optional)
        client_type: Client type (optional)
    """
    log_parts = [
        f"Request {request_id}",
        f"method={sanitize_log_output(method)}"
    ]
    
    if user_id:
        log_parts.append(f"user={sanitize_log_output(user_id)}")
    
    if client_type:
        log_parts.append(f"client={sanitize_log_output(client_type)}")
    
    logger.info(" | ".join(log_parts))


def log_security_event(logger: logging.Logger, event_type: str, details: str, 
                      request_id: str = None, user_id: str = None) -> None:
    """
    Log security-related events with standardized format.
    
    Args:
        logger: Logger instance
        event_type: Type of security event
        details: Event details
        request_id: Request identifier (optional)
        user_id: User identifier (optional)
    """
    log_parts = [
        f"SECURITY_EVENT: {event_type}",
        f"details={sanitize_log_output(details)}"
    ]
    
    if request_id:
        log_parts.append(f"request_id={request_id}")
    
    if user_id:
        log_parts.append(f"user={sanitize_log_output(user_id)}")
    
    logger.warning(" | ".join(log_parts))