"""
Integration test for the MCP (Model Context Protocol) server.

Unlike test_api.py (which tests REST endpoints via FastAPI's TestClient),
this test exercises the real MCP protocol handshake and tool invocation
against a live server, using the official MCP client SDK.

By default this runs against the production Azure deployment. Set the
MCP_TEST_URL environment variable to target a different server (e.g. a
local instance running on http://localhost:8000/mcp-server/mcp).
"""
import os
import pytest
from mcp.client.streamable_http import streamable_http_client
from mcp import ClientSession
import pytest

pytestmark = pytest.mark.integration
DEFAULT_MCP_URL = "https://rag-mcp-azure.redsand-f0795bb6.francecentral.azurecontainerapps.io/mcp-server/mcp"
MCP_URL = os.environ.get("MCP_TEST_URL", DEFAULT_MCP_URL)


@pytest.mark.asyncio
async def test_mcp_session_initializes():
    """A real MCP client can complete the protocol handshake against the server."""
    async with streamable_http_client(MCP_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            # No exception raised means the handshake succeeded.


@pytest.mark.asyncio
async def test_mcp_lists_search_documents_tool():
    """The server advertises the search_documents tool via MCP tool discovery."""
    async with streamable_http_client(MCP_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            tool_names = [t.name for t in tools.tools]
            assert "search_documents" in tool_names


@pytest.mark.asyncio
async def test_mcp_call_search_documents_returns_context():
    """Calling search_documents via MCP returns non-empty document context."""
    async with streamable_http_client(MCP_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "search_documents", {"query": "durée maximale contrat intérimaire"}
            )
            assert result.content
            text_blocks = [c.text for c in result.content if hasattr(c, "text")]
            assert any(text_blocks)
            assert "Extrait" in text_blocks[0]