"""
Base classes for MCP tools.

This module provides the abstract base class for implementing MCP tools
with proper validation, error handling, and logging.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

try:
    from ..utils import get_logger, sanitize_log_output
except ImportError:
    from datakwip_mcp.utils import get_logger, sanitize_log_output


logger = get_logger(__name__)


class ToolSchema(BaseModel):
    """Pydantic model for tool schema definition."""
    
    type: str = "object"
    properties: Dict[str, Dict[str, Any]]
    required: List[str] = Field(default_factory=list)


class ToolDefinition(BaseModel):
    """Pydantic model for complete tool definition."""
    
    name: str
    description: str
    inputSchema: ToolSchema


class ToolResult(BaseModel):
    """Pydantic model for tool execution result."""
    
    content: List[Dict[str, Any]]
    isError: bool = False


class BaseTool(ABC):
    """
    Abstract base class for MCP tools.
    
    All tools should inherit from this class and implement the required methods.
    """
    
    def __init__(self):
        """Initialize the tool."""
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name identifier."""
        pass
    
    @property
    @abstractmethod 
    def description(self) -> str:
        """Tool description for users."""
        pass
    
    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """Tool input schema definition."""
        pass
    
    @abstractmethod
    async def execute(self, arguments: Dict[str, Any], user_info: Optional[Dict[str, Any]] = None) -> ToolResult:
        """
        Execute the tool with given arguments.
        
        Args:
            arguments: Tool input arguments
            user_info: Optional user information from authentication
            
        Returns:
            ToolResult containing execution results
        """
        pass
    
    def get_definition(self) -> ToolDefinition:
        """
        Get the complete tool definition.
        
        Returns:
            ToolDefinition object
        """
        return ToolDefinition(
            name=self.name,
            description=self.description,
            inputSchema=ToolSchema(**self.input_schema)
        )
    
    def validate_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate tool arguments against schema.
        
        Args:
            arguments: Arguments to validate
            
        Returns:
            Validated arguments
            
        Raises:
            ValueError: If validation fails
        """
        schema = self.input_schema
        required_fields = schema.get("required", [])
        properties = schema.get("properties", {})
        
        # Check required fields
        missing_fields = [field for field in required_fields if field not in arguments]
        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")
        
        # Validate field types (basic validation)
        validated_args = {}
        for field_name, field_value in arguments.items():
            if field_name in properties:
                field_schema = properties[field_name]
                expected_type = field_schema.get("type")
                
                # Basic type validation
                if expected_type == "string" and not isinstance(field_value, str):
                    raise ValueError(f"Field '{field_name}' must be a string")
                elif expected_type == "number" and not isinstance(field_value, (int, float)):
                    raise ValueError(f"Field '{field_name}' must be a number")
                elif expected_type == "integer" and not isinstance(field_value, int):
                    raise ValueError(f"Field '{field_name}' must be an integer")
                elif expected_type == "boolean" and not isinstance(field_value, bool):
                    raise ValueError(f"Field '{field_name}' must be a boolean")
                
                validated_args[field_name] = field_value
            else:
                # Allow additional fields but log warning
                self.logger.warning(f"Unknown field '{field_name}' in tool arguments")
                validated_args[field_name] = field_value
        
        return validated_args
    
    async def safe_execute(self, arguments: Dict[str, Any], user_info: Optional[Dict[str, Any]] = None) -> ToolResult:
        """
        Safely execute the tool with error handling and logging.
        
        Args:
            arguments: Tool input arguments
            user_info: Optional user information
            
        Returns:
            ToolResult with execution results or error information
        """
        try:
            # Log tool execution
            user_id = user_info.get("username", "unknown") if user_info else "anonymous"
            self.logger.info(
                f"Executing tool '{self.name}' for user '{user_id}' with args: {sanitize_log_output(str(arguments))}"
            )
            
            # Validate arguments
            validated_args = self.validate_arguments(arguments)
            
            # Execute tool
            result = await self.execute(validated_args, user_info)
            
            self.logger.info(f"Tool '{self.name}' executed successfully")
            return result
            
        except ValueError as e:
            self.logger.warning(f"Tool '{self.name}' validation error: {str(e)}")
            return ToolResult(
                content=[{
                    "type": "text",
                    "text": f"Validation error: {str(e)}"
                }],
                isError=True
            )
        except Exception as e:
            self.logger.error(f"Tool '{self.name}' execution error: {str(e)}")
            return ToolResult(
                content=[{
                    "type": "text", 
                    "text": f"Tool execution failed: {str(e)}"
                }],
                isError=True
            )