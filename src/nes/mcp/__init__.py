"""MCP (Model Context Protocol) layer for NES."""

from nes.mcp.client import MCPClient
from nes.mcp.protocol import MCPError, MCPNotification, MCPRequest, MCPResponse
from nes.mcp.server import MCPServer
from nes.mcp.transport import (
    InProcessTransport,
    MCPTransport,
    SSETransport,
    StdioTransport,
    StreamableHTTPTransport,
)

__all__ = [
    "MCPClient",
    "MCPError",
    "MCPNotification",
    "MCPRequest",
    "MCPResponse",
    "MCPServer",
    "MCPTransport",
    "InProcessTransport",
    "SSETransport",
    "StdioTransport",
    "StreamableHTTPTransport",
]
