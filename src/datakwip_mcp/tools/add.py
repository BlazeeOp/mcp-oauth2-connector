"""
Add tool implementation.

This tool performs addition of two numbers, demonstrating mathematical
operations in the MCP server.
"""

from typing import Dict, Any, Optional

try:
    from .base import BaseTool, ToolResult
except ImportError:
    from datakwip_mcp.tools.base import BaseTool, ToolResult


class AddTool(BaseTool):
    """
    A mathematical addition tool that adds two numbers.
    
    This tool demonstrates numerical operations and input validation
    in the MCP server framework.
    """
    
    @property
    def name(self) -> str:
        """Tool name identifier."""
        return "add"
    
    @property
    def description(self) -> str:
        """Tool description for users.""" 
        return "Add two numbers together"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        """Tool input schema definition."""
        return {
            "type": "object",
            "properties": {
                "a": {
                    "type": "number",
                    "description": "First number to add",
                    "minimum": -1e10,  # Reasonable bounds
                    "maximum": 1e10
                },
                "b": {
                    "type": "number", 
                    "description": "Second number to add",
                    "minimum": -1e10,  # Reasonable bounds
                    "maximum": 1e10
                }
            },
            "required": ["a", "b"]
        }
    
    async def execute(self, arguments: Dict[str, Any], user_info: Optional[Dict[str, Any]] = None) -> ToolResult:
        """
        Execute the addition operation.
        
        Args:
            arguments: Tool arguments containing 'a' and 'b'
            user_info: Optional user information from authentication
            
        Returns:
            ToolResult containing the sum of the two numbers
        """
        a = arguments.get("a", 0)
        b = arguments.get("b", 0)
        
        # Validate number types and ranges
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            return ToolResult(
                content=[{
                    "type": "text",
                    "text": "Error: Both 'a' and 'b' must be numbers"
                }],
                isError=True
            )
        
        # Check for reasonable bounds to prevent overflow issues
        if abs(a) > 1e10 or abs(b) > 1e10:
            return ToolResult(
                content=[{
                    "type": "text",
                    "text": "Error: Numbers too large (maximum absolute value: 10,000,000,000)"
                }],
                isError=True
            )
        
        try:
            # Perform the addition
            result = a + b
            
            # Log the operation
            user_id = user_info.get("username", "unknown") if user_info else "anonymous"
            self.logger.info(f"Add tool: {a} + {b} = {result} for user: {user_id}")
            
            # Return the result
            return ToolResult(
                content=[{
                    "type": "text",
                    "text": f"{a} + {b} = {result}"
                }],
                isError=False
            )
            
        except Exception as e:
            self.logger.error(f"Addition operation failed: {str(e)}")
            return ToolResult(
                content=[{
                    "type": "text",
                    "text": f"Error performing addition: {str(e)}"
                }],
                isError=True
            )