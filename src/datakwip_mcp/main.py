"""
Main FastAPI application for the MCP Server.

This is the entry point for the secure MCP server with AWS Cognito OAuth2 authentication.
The application provides a clean, modular architecture with comprehensive security features.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
import secrets
import uvicorn
from fastapi import FastAPI, Request, Depends, Header, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

# Import our modules
try:
    # Try relative imports first (when run as module)
    from .config import get_cognito_config, get_server_config, get_client_configs
    from .auth import get_current_user, get_oauth_endpoints
    from .middleware import add_security_headers, get_cors_middleware, setup_rate_limiting
    from .tools import get_tool_registry
    from .utils import get_logger, detect_client_securely, sanitize_log_output, SecureErrorHandler
except ImportError:
    # Fall back to absolute imports (when run directly)
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from datakwip_mcp.config import get_cognito_config, get_server_config, get_client_configs
    from datakwip_mcp.auth import get_current_user, get_oauth_endpoints
    from datakwip_mcp.middleware import add_security_headers, get_cors_middleware, setup_rate_limiting
    from datakwip_mcp.tools import get_tool_registry
    from datakwip_mcp.utils import get_logger, detect_client_securely, sanitize_log_output, SecureErrorHandler


# Initialize logger
logger = get_logger(__name__)

# Load configuration
try:
    COGNITO_CONFIG = get_cognito_config()
    SERVER_CONFIG = get_server_config()
    CLIENT_CONFIGS = get_client_configs()
except ValueError as e:
    logger.critical(f"Failed to load configuration: {e}")
    raise


# Application lifespan manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Secure MCP Server")
    logger.info(f"Environment: {SERVER_CONFIG['environment']}")
    
    # Initialize tool registry and log available tools
    from .tools import get_tool_registry
    tool_registry = get_tool_registry()
    logger.info(f"Available tools: {tool_registry.get_tool_names()}")
    
    yield
    # Shutdown (if needed)
    logger.info("Shutting down Secure MCP Server")


# Initialize FastAPI app
app = FastAPI(
    title="Secure MCP Server with AWS Cognito OAuth2",
    description="A secure Model Context Protocol server with comprehensive security features",
    version="1.0.0",
    docs_url=None if SERVER_CONFIG["environment"] == "production" else "/docs",
    redoc_url=None if SERVER_CONFIG["environment"] == "production" else "/redoc",
    lifespan=lifespan
)

# Set up middleware
# 1. CORS (must be first to handle OPTIONS requests)
cors_middleware_class, cors_config = get_cors_middleware()
app.add_middleware(cors_middleware_class, **cors_config)

# 2. Security headers
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    return await add_security_headers(request, call_next)

# 3. Rate limiting
limiter = setup_rate_limiting(app)

# Initialize components
error_handler = SecureErrorHandler(logger)
tool_registry = get_tool_registry()

# Context storage (in-memory for demo)
contexts_db = {}


# Pydantic models
class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = {}
    id: Optional[Any] = None


class MCPResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[Any] = None


# OAuth2 endpoints
for endpoint_config in get_oauth_endpoints():
    if endpoint_config["method"] == "GET":
        app.get(endpoint_config["path"], name=endpoint_config["name"])(endpoint_config["handler"])
    elif endpoint_config["method"] == "POST":
        app.post(endpoint_config["path"], name=endpoint_config["name"])(endpoint_config["handler"])


# MCP Protocol Endpoints
@app.get("/.well-known/mcp")
@limiter.limit("20 per minute")
async def mcp_metadata(request: Request):
    """MCP server metadata endpoint following MCP specification."""
    logger.info("MCP Metadata endpoint accessed")
    logger.debug(f"Request headers: {dict(request.headers)}")
    
    # Detect client type
    client_type = detect_client_securely(request)
    client_config = CLIENT_CONFIGS.get(client_type, CLIENT_CONFIGS["default"])
    
    metadata = {
        "mcpVersion": "2025-06-18",
        "server": {
            "name": "Secure MCP Server",
            "version": "1.0.0"
        },
        "capabilities": {
            "tools": {
                "listChanged": True
            },
            "prompts": {},
            "resources": {}
        },
        "authentication": {
            "type": "oauth2",
            "oauth2": {
                "authorizationUrl": COGNITO_CONFIG["authorization_url"],
                "tokenUrl": COGNITO_CONFIG["token_url"],
                "clientId": client_config["client_id"],
                "scopes": COGNITO_CONFIG["scopes"]
            }
        }
    }
    
    logger.info(f"Returning MCP metadata for client {client_type}")
    return metadata


@app.get("/mcp")
@limiter.limit("30 per minute")
async def mcp_get(request: Request):
    """Handle GET requests to /mcp."""
    logger.info("MCP GET endpoint accessed")
    
    # Detect client type
    client_type = detect_client_securely(request)
    client_config = CLIENT_CONFIGS.get(client_type, CLIENT_CONFIGS["default"])
    
    # Base MCP metadata structure
    metadata = {
        "mcpVersion": "2025-06-18",
        "server": {
            "name": "Secure MCP Server", 
            "version": "1.0.0"
        },
        "capabilities": {
            "tools": {
                "listChanged": True
            },
            "prompts": {},
            "resources": {}
        }
    }
    
    # Check if request is authenticated
    auth_header = request.headers.get("authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        # UNAUTHENTICATED: Add authentication requirements
        metadata["authentication"] = {
            "type": "oauth2",
            "oauth2": {
                "authorizationUrl": COGNITO_CONFIG["authorization_url"],
                "tokenUrl": COGNITO_CONFIG["token_url"],
                "clientId": client_config["client_id"],
                "scopes": COGNITO_CONFIG["scopes"]
            }
        }
        logger.info(f"Returning MCP metadata with auth requirements for {client_type}")
    else:
        logger.info(f"Returning MCP metadata for authenticated {client_type} client")
    
    return metadata


@app.head("/mcp")
@limiter.limit("30 per minute")
async def mcp_head(request: Request):
    """Handle HEAD requests to /mcp."""
    logger.info("MCP HEAD endpoint accessed")
    return Response()


# Context endpoints
@app.get("/v1/contexts")
@limiter.limit("10 per minute")
async def get_contexts(request: Request, user: Dict[str, Any] = Depends(get_current_user)):
    """Get all contexts for authenticated user."""
    user_id = user.get("sub", "unknown")
    user_contexts = [ctx for ctx in contexts_db.values() if ctx.get("user_id") == user_id]
    
    logger.info(f"Retrieved {len(user_contexts)} contexts for user: {user.get('username', 'unknown')}")
    return {"contexts": user_contexts}


@app.post("/v1/contexts")
@limiter.limit("5 per minute") 
async def create_context(request: Request, context_data: dict, user: Dict[str, Any] = Depends(get_current_user)):
    """Create a new context for authenticated user."""
    import uuid
    
    user_id = user.get("sub", "unknown")
    context_id = str(uuid.uuid4())
    
    new_context = {
        "id": context_id,
        "user_id": user_id,
        "created_at": "2025-01-15T00:00:00Z",  # Should use proper timestamp
        **context_data
    }
    
    contexts_db[context_id] = new_context
    logger.info(f"Created context {context_id} for user: {user.get('username', 'unknown')}")
    
    return {"context": new_context}


# Main MCP handler
@app.post("/mcp")
@limiter.limit("50 per minute")
async def mcp_handler(
    request: Request,
    mcp_request: MCPRequest,
    mcp_protocol_version: str = Header(None, alias="MCP-Protocol-Version"),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Main MCP protocol handler with authentication."""
    
    # Generate request ID for tracking
    request_id = secrets.token_hex(8)
    
    # Detect client for logging
    client_type = detect_client_securely(request)
    
    logger.info(f"MCP request {request_id}: method={sanitize_log_output(mcp_request.method)}, client={client_type}")
    logger.info(f"User: {user.get('username', 'unknown')} (ID: {user.get('sub', 'unknown')})")
    
    try:
        if mcp_request.method == "initialize":
            logger.info(f"Processing initialize request from {client_type}")
            response = MCPResponse(
                jsonrpc="2.0",
                result={
                    "protocolVersion": "2025-06-18",
                    "capabilities": {
                        "tools": {
                            "listChanged": True
                        },
                        "prompts": {},
                        "resources": {}
                    },
                    "serverInfo": {
                        "name": "Secure MCP Server with AWS Cognito OAuth2",
                        "version": "1.0.0"
                    }
                },
                id=mcp_request.id
            )
            return Response(
                content=response.model_dump_json(),
                media_type="application/json",
                status_code=200,
                headers={"MCP-Protocol-Version": "2025-06-18"}
            )

        elif mcp_request.method == "notifications/initialized":
            logger.info(f"Processing notifications/initialized from {client_type}")
            response = MCPResponse(
                jsonrpc="2.0",
                result={},
                id=mcp_request.id if mcp_request.id else None
            )
            return Response(
                content=response.model_dump_json(),
                media_type="application/json",
                status_code=202,  # 202 Accepted for notifications
                headers={"MCP-Protocol-Version": "2025-06-18"}
            )

        elif mcp_request.method == "tools/list":
            logger.info(f"Tools/list method called from {client_type}")
            
            # Get tools from registry
            tool_definitions = tool_registry.list_tools()
            tools = [tool.dict() for tool in tool_definitions]
            
            response = MCPResponse(
                jsonrpc="2.0",
                result={"tools": tools},
                id=mcp_request.id
            )
            return Response(
                content=response.model_dump_json(),
                media_type="application/json",
                status_code=200,
                headers={"MCP-Protocol-Version": "2025-06-18"}
            )

        elif mcp_request.method == "prompts/list":
            logger.info(f"Prompts/list method called from {client_type}")
            response = MCPResponse(
                jsonrpc="2.0",
                result={"prompts": []},  # Empty for now
                id=mcp_request.id
            )
            return Response(
                content=response.model_dump_json(),
                media_type="application/json",
                status_code=200,
                headers={"MCP-Protocol-Version": "2025-06-18"}
            )

        elif mcp_request.method == "resources/list":
            logger.info(f"Resources/list method called from {client_type}")
            response = MCPResponse(
                jsonrpc="2.0",
                result={"resources": []},  # Empty for now
                id=mcp_request.id
            )
            return Response(
                content=response.model_dump_json(),
                media_type="application/json",
                status_code=200,
                headers={"MCP-Protocol-Version": "2025-06-18"}
            )

        elif mcp_request.method == "tools/call":
            tool_name = mcp_request.params.get("name")
            arguments = mcp_request.params.get("arguments", {})
            
            logger.info(f"Tools/call: {tool_name} from {client_type}")
            
            # Execute tool using registry
            try:
                result = await tool_registry.execute_tool(tool_name, arguments, user)
                
                response = MCPResponse(
                    jsonrpc="2.0",
                    result={"content": result.content},
                    id=mcp_request.id
                )
                
                if result.isError:
                    logger.warning(f"Tool {tool_name} returned error")
                
            except ValueError as e:
                logger.warning(f"Tool not found: {tool_name}")
                response = MCPResponse(
                    jsonrpc="2.0",
                    error={"code": -32602, "message": f"Unknown tool: {tool_name}"},
                    id=mcp_request.id
                )
            
            return Response(
                content=response.model_dump_json(),
                media_type="application/json",
                status_code=200,
                headers={"MCP-Protocol-Version": "2025-06-18"}
            )

        else:
            logger.warning(f"Unknown method called: {mcp_request.method}")
            response = MCPResponse(
                jsonrpc="2.0",
                error={"code": -32601, "message": f"Method not found: {mcp_request.method}"},
                id=mcp_request.id
            )
            return Response(
                content=response.model_dump_json(),
                media_type="application/json",
                status_code=200,
                headers={"MCP-Protocol-Version": "2025-06-18"}
            )

    except Exception as e:
        logger.error(f"Error processing MCP request {request_id}: {str(e)}")
        error_info = error_handler.get_safe_error_message(e, request_id)
        
        response = MCPResponse(
            jsonrpc="2.0",
            error={
                "code": -32603, 
                "message": error_info["error"],
                "data": {"error_id": error_info["error_id"]}
            },
            id=mcp_request.id
        )
        return Response(
            content=response.model_dump_json(),
            media_type="application/json",
            status_code=500,
            headers={"MCP-Protocol-Version": "2025-06-18"}
        )

@app.get("/health")
@limiter.limit("100 per minute")
async def health_check(request: Request):
    """Health check endpoint."""
    return {
        "status": "healthy", 
        "service": "Secure MCP Server with AWS Cognito OAuth2",
        "version": "1.0.0"
    }


@app.get("/")
@limiter.limit("50 per minute")
async def root(request: Request):
    """Root endpoint with server info."""
    return {
        "name": "Secure MCP Server",
        "description": "MCP server with AWS Cognito OAuth2 authentication",
        "version": "1.0.0",
        "endpoints": {
            "mcp": "/mcp",
            "metadata": "/.well-known/mcp",
            "health": "/health"
        }
    }




def main():
    """Main entry point for the application."""
    if SERVER_CONFIG["environment"] == "development":
        # For development, use import string to enable reload
        uvicorn.run(
            "datakwip_mcp.main:app",
            host="0.0.0.0",
            port=8000,
            log_level=SERVER_CONFIG["log_level"].lower(),
            reload=True
        )
    else:
        # For production, use app object directly
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level=SERVER_CONFIG["log_level"].lower(),
            reload=False
        )


if __name__ == "__main__":
    main()