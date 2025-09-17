"""
Echo tool implementation.

This tool echoes back the provided message, useful for testing and debugging
the MCP server functionality.
"""

from typing import Dict, Any, Optional

try:
    from .base import BaseTool, ToolResult
    from ..utils import sanitize_log_output
except ImportError:
    from datakwip_mcp.tools.base import BaseTool, ToolResult
    from datakwip_mcp.utils import sanitize_log_output


class EchoTool(BaseTool):
    """
    A simple echo tool that returns the input message.
    
    This tool is useful for testing MCP server functionality and
    verifying that tools are working correctly.
    """
    
    @property
    def name(self) -> str:
        """Tool name identifier."""
        return "echo"
    
    @property
    def description(self) -> str:
        """Tool description for users."""
        return "Echo back the provided message"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        """Tool input schema definition."""
        return {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The message to echo back",
                    "maxLength": 1000  # Limit message length for security
                }
            },
            "required": ["message"]
        }
    
    async def execute(self, arguments: Dict[str, Any], user_info: Optional[Dict[str, Any]] = None) -> ToolResult:
        """
        Execute the echo tool.
        
        Args:
            arguments: Tool arguments containing 'message'
            user_info: Optional user information from authentication
            
        Returns:
            ToolResult containing the echoed message
        """
        message = arguments.get("message", "")
        
        # Log the echo operation
        user_id = user_info.get("username", "unknown") if user_info else "anonymous"
        self.logger.info(f"Echo tool called with message: '{sanitize_log_output(message)}' by user: {user_id}")
        
        # Validate message length (additional security check)
        if len(message) > 1000:
            self.logger.warning(f"Echo message too long: {len(message)} characters")
            return ToolResult(
                content=[{
                    "type": "text",
                    "text": "Error: Message too long (maximum 1000 characters)"
                }],
                isError=True
            )
        
        # Return the echoed message
        return ToolResult(
            content=[{
                "type": "text",
                "text": f"Echo: {message}"
            }],
            isError=False
        )