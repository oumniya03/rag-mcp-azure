import os
import sys
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from mcp.server.transport_security import TransportSecuritySettings
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
    """Search the RAG knowledge base for relevant document chunks matching a query.
    
    Args:
        query (str): The search query to find relevant document chunks (e.g., 'What is the contract duration?')
    
    Returns:
        str: The most relevant document chunks from the knowledge base.
    """
    return rag_engine.search(query, k=3)


# DNS rebinding protection: allow localhost (dev) and the production Azure host
AZURE_HOST = "rag-mcp-azure.redsand-f0795bb6.francecentral.azurecontainerapps.io"

security_settings = TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=[
        "127.0.0.1:*",
        "localhost:*",
        "[::1]:*",
        AZURE_HOST,
    ],
    allowed_origins=[
        "http://127.0.0.1:*",
        "http://localhost:*",
        "http://[::1]:*",
        f"https://{AZURE_HOST}",
    ],
)

# Create the MCP sub-app once, with security settings (this lazily initializes the session_manager)
mcp_app = mcp.streamable_http_app(transport_security=security_settings)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # The MCP session manager needs an active task group before it can handle requests
    async with mcp.session_manager.run():
        yield


app = FastAPI(
    title="RAG MCP Azure",
    description="FastAPI exposing a lightweight RAG search engine and MCP-compatible tool.",
    version="0.1.0",
    lifespan=lifespan,
)

# Mount the MCP server. mcp_app already exposes its routes under /mcp internally,
# so we mount it at /mcp-server to avoid a double /mcp/mcp prefix while keeping REST routes at root.
app.mount("/mcp-server", mcp_app)


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


@app.post("/reindex")
def reindex():
    """Refresh the in-memory FAISS index from Blob Storage or local files."""
    message = rag_engine.ingest()
    return {"status": message}


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload a PDF document and add it to the RAG index (ephemeral, session-scoped)."""
    if not file.filename.endswith(".pdf"):
        return {"status": "Erreur: Veuillez charger un fichier PDF.", "success": False}

    try:
        pdf_bytes = await file.read()
        message = rag_engine.add_documents_from_bytes(pdf_bytes, source_name=file.filename)
        return {"status": message, "success": True, "filename": file.filename}
    except Exception as e:
        return {"status": f"Erreur lors de l'upload: {str(e)}", "success": False}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

