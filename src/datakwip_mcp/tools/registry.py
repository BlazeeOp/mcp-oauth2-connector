"""
Tool registry for managing MCP tools.

This module provides a centralized registry for managing and accessing
MCP tools, including validation and discovery capabilities.
"""

from typing import Dict, List, Optional, Type
try:
    from .base import BaseTool, ToolDefinition
    from .echo import EchoTool
    from .add import AddTool
    from ..utils import get_logger
except ImportError:
    from datakwip_mcp.tools.base import BaseTool, ToolDefinition
    from datakwip_mcp.tools.echo import EchoTool
    from datakwip_mcp.tools.add import AddTool
    from datakwip_mcp.utils import get_logger


logger = get_logger(__name__)


class ToolRegistry:
    """
    Registry for managing MCP tools.
    
    This class provides centralized management of available tools,
    including registration, discovery, and execution capabilities.
    """
    
    def __init__(self):
        """Initialize the tool registry."""
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()
    
    def _register_default_tools(self) -> None:
        """Register the default set of tools."""
        default_tools = [
            EchoTool(),
            AddTool()
        ]
        
        for tool in default_tools:
            self.register_tool(tool)
        
        logger.info(f"Registered {len(default_tools)} default tools")
    
    def register_tool(self, tool: BaseTool) -> None:
        """
        Register a tool in the registry.
        
        Args:
            tool: Tool instance to register
            
        Raises:
            ValueError: If tool name conflicts with existing tool
        """
        if not isinstance(tool, BaseTool):
            raise ValueError("Tool must inherit from BaseTool")
        
        tool_name = tool.name
        
        if tool_name in self._tools:
            logger.warning(f"Overwriting existing tool: {tool_name}")
        
        self._tools[tool_name] = tool
        logger.info(f"Registered tool: {tool_name}")
    
    def unregister_tool(self, tool_name: str) -> bool:
        """
        Unregister a tool from the registry.
        
        Args:
            tool_name: Name of tool to unregister
            
        Returns:
            True if tool was unregistered, False if not found
        """
        if tool_name in self._tools:
            del self._tools[tool_name]
            logger.info(f"Unregistered tool: {tool_name}")
            return True
        
        logger.warning(f"Attempted to unregister unknown tool: {tool_name}")
        return False
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """
        Get a tool by name.
        
        Args:
            tool_name: Name of the tool to retrieve
            
        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(tool_name)
    
    def list_tools(self) -> List[ToolDefinition]:
        """
        Get list of all registered tool definitions.
        
        Returns:
            List of tool definitions
        """
        return [tool.get_definition() for tool in self._tools.values()]
    
    def get_tool_names(self) -> List[str]:
        """
        Get list of all registered tool names.
        
        Returns:
            List of tool names
        """
        return list(self._tools.keys())
    
    def tool_exists(self, tool_name: str) -> bool:
        """
        Check if a tool exists in the registry.
        
        Args:
            tool_name: Name of tool to check
            
        Returns:
            True if tool exists, False otherwise
        """
        return tool_name in self._tools
    
    async def execute_tool(self, tool_name: str, arguments: Dict, user_info: Optional[Dict] = None):
        """
        Execute a tool by name.
        
        Args:
            tool_name: Name of tool to execute
            arguments: Tool arguments
            user_info: Optional user information
            
        Returns:
            Tool execution result
            
        Raises:
            ValueError: If tool not found
        """
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")
        
        return await tool.safe_execute(arguments, user_info)
    
    def get_registry_stats(self) -> Dict[str, int]:
        """
        Get statistics about the tool registry.
        
        Returns:
            Dict containing registry statistics
        """
        return {
            "total_tools": len(self._tools),
            "tool_names": self.get_tool_names()
        }


# Global tool registry instance
_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """
    Get the global tool registry instance.
    
    Returns:
        Global ToolRegistry instance
    """
    global _tool_registry
    
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
        logger.info("Initialized global tool registry")
    
    return _tool_registry


def register_custom_tool(tool: BaseTool) -> None:
    """
    Register a custom tool in the global registry.
    
    Args:
        tool: Custom tool to register
    """
    registry = get_tool_registry()
    registry.register_tool(tool)