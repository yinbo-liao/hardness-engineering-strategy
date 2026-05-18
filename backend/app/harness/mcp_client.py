import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from backend.app.config import get_settings


@dataclass
class MCPToolDefinition:
    name: str
    description: str
    input_schema: dict
    annotations: Optional[dict] = None


@dataclass
class MCPToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class MCPResponse:
    content: list
    is_error: bool = False
    metadata: dict = field(default_factory=dict)


class MCPClient:
    """
    Model Context Protocol client for Claude Code integration.

    Implements the MCP protocol lifecycle:
    1. Initialize — negotiate protocol version and capabilities
    2. List tools — discover available sandbox tools
    3. Call tool — invoke with validated arguments
    4. Receive result — parse and return structured output
    """

    def __init__(self, server_url: Optional[str] = None):
        settings = get_settings()
        self.server_url = server_url or settings.MCP_SERVER_URL
        self.api_key = settings.CLAUDE_API_KEY
        self.model = settings.CLAUDE_MODEL
        self._initialized = False
        self._server_tools: Dict[str, MCPToolDefinition] = {}
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(300.0))

    async def initialize(self) -> dict:
        response = await self._request(
            "initialize",
            {
                "protocol_version": "2024-11-05",
                "capabilities": {"tools": {}, "resources": {}},
                "client_info": {"name": "harness-orchestrator", "version": "1.0.0"},
            },
        )
        self._initialized = True
        return response

    async def list_tools(self) -> List[MCPToolDefinition]:
        if not self._initialized:
            await self.initialize()

        result = await self._request("tools/list", {})
        tools = []
        for t in result.get("tools", []):
            tools.append(
                MCPToolDefinition(
                    name=t["name"],
                    description=t.get("description", ""),
                    input_schema=t.get("inputSchema", {}),
                    annotations=t.get("annotations"),
                )
            )
        self._server_tools = {t.name: t for t in tools}
        return tools

    async def call_tool(self, name: str, arguments: dict) -> MCPResponse:
        if not self._initialized:
            await self.initialize()

        result = await self._request(
            "tools/call",
            {"name": name, "arguments": arguments},
        )
        return MCPResponse(
            content=result.get("content", []),
            is_error=result.get("isError", False),
            metadata=result.get("_meta", {}),
        )

    async def send_prompt(self, prompt: str, context: Optional[dict] = None) -> dict:
        """Send a structured prompt with context to Claude via MCP."""
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4096,
        }
        if context:
            payload["context"] = context

        response = await self._client.post(
            f"{self.server_url}/v1/messages",
            json=payload,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return response.json()

    async def _request(self, method: str, params: dict) -> dict:
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": str(time.time_ns()),
        }
        response = await self._client.post(
            f"{self.server_url}/mcp",
            json=payload,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            raise RuntimeError(
                f"MCP error: {data['error'].get('message', 'unknown')}"
            )
        return data.get("result", {})

    def _auth_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    async def close(self) -> None:
        await self._client.aclose()
