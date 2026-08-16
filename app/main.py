import os
import sys

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

from mcp.server.mcpserver import MCPServer

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from app.rag_engine import rag_engine
else:
    from app.rag_engine import rag_engine

# MCP v2 API: tool exposed to external agents, while the final answer remains client-side.
mcp = MCPServer("rag-agent-server")


@mcp.tool()
def search_documents(query: str) -> str:
    """Return the most relevant document chunks for the incoming question."""
    return rag_engine.search(query, k=3)


app = FastAPI(
    title="RAG MCP Azure",
    description="FastAPI exposing a lightweight RAG search engine and MCP-compatible tool.",
    version="0.1.0",
)


@app.get("/")
def root():
    return {"message": "Serveur MCP RAG actif. Le système est en ligne !"}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


class QueryRequest(BaseModel):
    query: str


@app.post("/query")
def query_rag(request: QueryRequest):
    """Return only the retrieved context, without any final LLM synthesis."""
    context = rag_engine.search(request.query, k=3)
    return {
        "query": request.query,
        "context_extrait": context,
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

