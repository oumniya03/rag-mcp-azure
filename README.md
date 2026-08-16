# RAG MCP Azure - Lightweight Retrieval-Augmented Generation Service

A production-ready **Retrieval-Augmented Generation (RAG)** API deployed on **Azure Container Apps**. Built for efficiency with a CPU-only footprint, in-memory vector storage, and MCP tool compatibility.

---

## 🎯 Project Overview

**What it does:**
- Ingests PDF documents from local storage
- Chunks and embeds them using sentence transformers
- Stores embeddings in FAISS (in-memory vector store)
- Serves FastAPI HTTP endpoints for document retrieval
- Exposes an MCP-compatible tool for downstream applications
- Returns only relevant document context (no final LLM synthesis)

**Design philosophy:**
- Lightweight: Optimized for 8 GB RAM, CPU-only environments
- Serverless: Deployed on Azure Container Apps (auto-scaling, managed infrastructure)
- Cost-effective: No heavy vector databases or GPU requirements
- Production-ready: Automated CI/CD with GitHub Actions

---

## 📊 Tech Stack

| Component | Technology | Notes |
|-----------|-----------|-------|
| **Framework** | FastAPI + Uvicorn | Async HTTP server |
| **RAG Engine** | LangChain + FAISS | PDF loading, text splitting, embeddings, vector search |
| **Embeddings** | HuggingFace Sentence Transformers | CPU-optimized models (all-MiniLM-L6-v2) |
| **MCP Server** | MCP v2 (mcp.server.mcpserver) | Tool interface for retrieval |
| **Containerization** | Docker | CPU-optimized image (Python 3.12-slim, no GPU torch) |
| **Orchestration** | Azure Container Apps | Managed Kubernetes, auto-scaling, ingress |
| **Container Registry** | Azure Container Registry (ACR) | Image storage and management |
| **CI/CD** | GitHub Actions | Automated build, push, and deploy |

---

## 🏗️ Project Structure

```
rag-mcp-azure/
├── app/
│   ├── data/                    # PDF documents for RAG
│   │   └── *.pdf
│   ├── main.py                  # FastAPI app + MCP server
│   └── rag_engine.py            # RAG logic (ingestion, search)
├── .github/
│   └── workflows/
│       └── deploy.yml           # GitHub Actions CI/CD pipeline
├── scripts/
│   └── deploy-aca.sh            # Manual Azure deployment script
├── Dockerfile                    # Production image definition
├── .dockerignore                 # Optimize Docker context
├── .gitignore                    # Git ignore rules
├── requirements.txt              # Python dependencies
├── README.md                     # This file
└── CLAUDE_PROMPT.md             # Diagnostic context (for debugging)
```

---

## 🔌 MCP Protocol Integration

### What is MCP?

**Model Context Protocol (MCP)** is an open standard for connecting AI agents to external tools and data sources. Instead of embedding knowledge retrieval inside an LLM, MCP exposes it as a **discoverable tool** that any compatible agent (Claude, Gemini, custom LLMs) can invoke over a standard transport.

**Key advantage for interviews:** Demonstrates a real, working implementation of an emerging agentic AI standard — not just a REST API with an MCP label attached.

### Transport & Endpoint

This server exposes MCP over **Streamable HTTP** (the modern MCP transport, superseding SSE), mounted on the same FastAPI app that serves the REST endpoints.

| Environment | MCP endpoint |
|---|---|
| Local | `http://localhost:8000/mcp-server/mcp` |
| Production | `https://rag-mcp-azure.redsand-f0795bb6.francecentral.azurecontainerapps.io/mcp-server/mcp` |

The MCP session manager is initialized via FastAPI's `lifespan`, so it starts and stops cleanly alongside the web server (see `app/main.py`).

### Exposed Tool

| Tool | Input | Output | Purpose |
|------|-------|--------|----------|
| `search_documents` | `query: string` | Document chunks (top-3 by relevance) | Search the RAG knowledge base |

### Tool Schema

```json
{
  "tools": [
    {
      "name": "search_documents",
      "description": "Search the RAG knowledge base for relevant document chunks matching a query.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "query": {
            "type": "string",
            "description": "The search query to find relevant document chunks (e.g., 'What is the contract duration?')"
          }
        },
        "required": ["query"]
      }
    }
  ]
}
```

### A note on testing with `curl`

A plain `curl` GET request to the MCP endpoint will return a `400 Bad Request` with a JSON-RPC error like:

```json
{"jsonrpc":"2.0","id":null,"error":{"code":-32600,"message":"Bad Request: Missing session ID"}}
```

**This is expected, not a bug.** MCP over Streamable HTTP requires a session handshake before any tool call — `curl` alone doesn't perform this. This response actually confirms the server correctly speaks the MCP JSON-RPC protocol; it's just rejecting an incomplete request. A real MCP client handles this handshake automatically.

### Connect with an MCP Client

**Claude Desktop** (`claude_desktop_config.json` — on Windows: `%APPDATA%\Claude\claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "rag-mcp-azure": {
      "url": "https://rag-mcp-azure.redsand-f0795bb6.francecentral.azurecontainerapps.io/mcp-server/mcp"
    }
  }
}
```

*(Exact config keys depend on your MCP client version — some clients use `url`, others require a `transport: "streamable_http"` field. Check your client's MCP documentation if the connection fails.)*

**Python MCP client** (for scripted testing):

```python
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession

async def test_search():
    url = "https://rag-mcp-azure.redsand-f0795bb6.francecentral.azurecontainerapps.io/mcp-server/mcp"
    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("search_documents", {"query": "durée maximale contrat intérimaire"})
            print(result)
```

### Known limitation

The MCP mount path (`/mcp-server/mcp`) is a workaround for a routing conflict between the MCP SDK's internal `/mcp` route and FastAPI's REST routes at root level. A cleaner path structure is a possible future improvement, but the current setup is fully functional and tested.

---

## �🚀 Quick Start

### Local Development

**1. Clone and setup:**
```bash
git clone https://github.com/oumniya03/rag-mcp-azure.git
cd rag-mcp-azure
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate
pip install -r requirements.txt
```

**2. Add PDF documents:**
```bash
# Place your PDF files in app/data/
cp your-documents.pdf app/data/
```

**3. Run locally:**
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**4. Test the endpoints:**

Health check:
```bash
curl http://localhost:8000/health
# Response: {"status":"ok"}
```

RAG query:
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query":"What is the contract duration?"}'
```

Response format:
```json
{
  "query": "What is the contract duration?",
  "context_extrait": "Excerpt 1:\n...\n\nExcerpt 2:\n..."
}
```

---

## 🐳 Docker

### Build locally
```bash
docker build -t rag-mcp-azure:latest .
```

### Run locally
```bash
docker run --rm -p 8000:8000 rag-mcp-azure:latest
```

### Image size optimization
- **Base image:** `python:3.12.8-slim` (~150 MB)
- **Torch:** CPU-only wheel (no CUDA libraries)
- **Cache layers:** Maximize reuse during builds
- **Result:** ~500 MB final image (compressed on ACR)

---

## 📦 Azure Blob Storage Integration

This service can ingest documents from **Azure Blob Storage** instead of (or in addition to) local files. This is the recommended approach for production deployments.

### Architecture

```
┌──────────────────────────────────────┐
│   Azure Blob Storage (documents/)    │
│   - sample-contract.pdf              │
│   - guide.pdf                        │
└──────────────────┬───────────────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │  RAG Engine          │
        │ (rag_engine.py)      │
        │ - Load from Blob     │
        │ - Chunk & embed      │
        └──────────────────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │  FAISS Index         │
        │  (in-memory)         │
        └──────────────────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │  FastAPI Endpoints   │
        │  /query, /reindex    │
        └──────────────────────┘
```

### Setup Instructions

**1. Create a Blob Storage account (Azure Portal or CLI):**

```powershell
# Create storage account (replace with your values)
az storage account create --name ragstgaccount --resource-group rg-rag-mcp-azure --location francecentral

# Create a container named "documents"
az storage container create --name documents --account-name ragstgaccount

# Get connection string
az storage account show-connection-string --name ragstgaccount --resource-group rg-rag-mcp-azure
```

**2. Upload PDF files to the container:**

```powershell
az storage blob upload --account-name ragstgaccount --container-name documents --file your-document.pdf --name your-document.pdf
```

**3. Set environment variable on Azure Container Apps:**

```powershell
# Get the connection string
$connString = az storage account show-connection-string --name ragstgaccount --resource-group rg-rag-mcp-azure --query connectionString -o tsv

# Update Container App with the environment variable
az containerapp update `
  --name rag-mcp-azure `
  --resource-group rg-rag-mcp-azure `
  --set-env-vars BLOB_CONTAINER_URL=$connString
```

**4. Trigger reindexing:**

```bash
curl -X POST http://localhost:8000/reindex
# Response: {"status": "Réindexation réussie."}
```

### How it Works

- **On startup:** If `BLOB_CONTAINER_URL` environment variable is set, the service will download all PDFs from Blob Storage. Otherwise, it falls back to local `app/data/` folder.
- **On `/reindex` call:** The service re-downloads all documents and rebuilds the FAISS index.
- **Ephemeral uploads:** Documents uploaded via `/upload` are added to the in-memory index but are **not** persisted to Blob Storage. They will be lost on service restart.

---

## ☁️ Azure Deployment

### Current Production Environment

**Live URL:** `https://rag-mcp-azure.redsand-f0795bb6.francecentral.azurecontainerapps.io`

**Resources:**
- **Container App Name:** `rag-mcp-azure`
- **Resource Group:** `rg-rag-mcp-azure`
- **ACA Environment:** `cae-rag-mcp-azure`
- **Region:** France Central
- **ACR:** `ragmcpacr26` (in `rg-rag-mcp-ne`)
- **Compute:** 0.5 CPU, 1.0 Gi memory

### GitHub Secrets (Required)

Set these in your GitHub repository settings:

| Secret | Description |
|--------|-------------|
| `AZURE_CREDENTIALS` | Service principal JSON (from `az ad sp create-for-rbac --sdk-auth`) |
| `ACR_USERNAME` | ACR admin username (from `az acr credential show`) |
| `ACR_PASSWORD` | ACR admin password (from `az acr credential show`) |

### Deployment Pipeline

The workflow [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml) runs on every push to `main`:

1. **Checkout code**
2. **Python setup** (3.12)
3. **Dependency installation** and smoke test
4. **Azure login** (service principal)
5. **Docker setup** (Buildx for multi-arch builds)
6. **Docker login** to ACR
7. **Build and push** image to ACR
8. **Azure CLI steps:**
   - Add Container App extension
   - Verify ACA environment exists
   - Create or update Container App with new image

**Deploy on push:**
```bash
git push origin main  # Triggers the workflow
```

**Manual deploy (if needed):**
```bash
bash scripts/deploy-aca.sh
```

---

## 📡 API Endpoints

### GET /health
Health check endpoint.

**Response:**
```json
{"status": "ok"}
```

### POST /query
Retrieve document context for a given query.

**Request:**
```json
{"query": "your question here"}
```

**Response:**
```json
{
  "query": "your question here",
  "context_extrait": "Excerpt 1:\n...\n\nExcerpt 2:\n...\n\nExcerpt 3:\n..."
}
```

### POST /reindex
Refresh the in-memory FAISS index from Blob Storage (if configured) or local files.

**Request:** (no body required)
```bash
curl -X POST http://localhost:8000/reindex
```

**Response:**
```json
{
  "status": "Réindexation réussie."
}
```

**Use case:** After uploading new PDFs to Blob Storage, call this endpoint to update the search index without restarting the service.

### POST /upload
Upload a PDF document and add it to the RAG index (ephemeral, session-scoped).

**Request:**
```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@your-document.pdf"
```

**Response:**
```json
{
  "status": "Succès: 42 chunks ajoutés à l'index.",
  "success": true,
  "filename": "your-document.pdf"
}
```

**Important:** Uploaded documents are added only to the in-memory FAISS index and will be **lost when the service restarts**. To persist documents, upload them directly to Blob Storage instead.

---

## 🔧 Configuration

### Environment variables
- `BLOB_CONTAINER_URL` (optional): Azure Blob Storage connection string. If set, documents will be loaded from Blob Storage instead of local files. Example: `DefaultEndpointsProtocol=https;AccountName=...`

### Local tweaking
Edit `app/rag_engine.py` to customize:
- `DATA_DIR`: PDF source folder
- `CHUNK_SIZE`: Text chunk size for splitting (default: 500)
- `OVERLAP`: Chunk overlap (default: 100)
- `K`: Number of results returned (default: 3)
- Embedding model: Change `HuggingFaceEmbeddings` model name

---

## 📖 Key Files Explained

### app/main.py
- FastAPI application with four REST endpoints (`/health`, `/query`, `/reindex`, `/upload`)
- MCP server (Streamable HTTP) mounted at `/mcp-server/mcp`, exposing the `search_documents` tool
- FastAPI `lifespan` manages the MCP session manager's async lifecycle
- Request/response models

### app/rag_engine.py
- `SimpleRAGEngine` class: orchestrates RAG pipeline
- `initialize_store()`: loads PDFs, chunks, embeds, indexes
- `ingest()`: adds documents to FAISS
- `search()`: similarity search on queries

### Dockerfile
- Multi-stage build (compile Python dependencies)
- CPU-only torch wheel (no GPU libraries)
- Minimal layer footprint
- Runs as non-root user

### .github/workflows/deploy.yml
- GitHub Actions workflow for CI/CD
- Builds Docker image, pushes to ACR
- Deploys to Azure Container Apps
- Full automation on `main` branch push

---

## 🧪 Testing

### Local unit test
```bash
python -m compileall app
```

### Local smoke test (app imports)
```python
from app.main import app
from app.rag_engine import SimpleRAGEngine
print("All imports OK")
```

### Production endpoint test (PowerShell)
```powershell
# Health
Invoke-WebRequest -Uri "https://rag-mcp-azure.redsand-f0795bb6.francecentral.azurecontainerapps.io/health" `
  -Method GET -UseBasicParsing

# Query
$body = @{query="test"} | ConvertTo-Json
Invoke-WebRequest -Uri "https://rag-mcp-azure.redsand-f0795bb6.francecentral.azurecontainerapps.io/query" `
  -Method POST -ContentType "application/json" -Body $body -UseBasicParsing
```

---

## 🔐 Azure Prerequisites (First-time setup)

### 1. Register Microsoft.App provider (one-time)
```bash
az provider register --namespace Microsoft.App --wait
```

### 2. Create service principal
```bash
az ad sp create-for-rbac --name "rag-mcp-github" --role Contributor --sdk-auth
# Copy the JSON output → Set as AZURE_CREDENTIALS secret in GitHub
```

### 3. Enable ACR admin account
```bash
az acr update --name ragmcpacr26 --admin-enabled true
az acr credential show --name ragmcpacr26
# Copy username/password → Set as ACR_USERNAME, ACR_PASSWORD secrets in GitHub
```

### 4. Verify ACA environment
```bash
az containerapp env list -o table
# Should show: cae-rag-mcp-azure in rg-rag-mcp-azure, France Central
```

---

## ⚙️ Troubleshooting

### Docker build fails
- Check `requirements.txt` for incompatible packages
- Ensure Python 3.12 compatibility
- Review Dockerfile for typos

### GitHub Actions workflow fails
- Check secrets are set in repository settings
- Verify ACR admin is enabled
- Run `az containerapp env show` locally to confirm environment exists
- Look for `--location` parameter errors (removed from `az containerapp create`)

### PDF documents not found
- Ensure PDFs are in `app/data/`
- Check file permissions
- Try absolute path in `rag_engine.py` DATA_DIR

### /query endpoint returns empty context
- Check that PDFs exist in `app/data/`
- Run locally and check console output for ingestion logs
- Verify FAISS index is populated

---

## 📈 Performance & Constraints

| Metric | Value |
|--------|-------|
| Target RAM | 8 GB |
| Deployment CPU | 0.5 CPU |
| Deployment Memory | 1.0 Gi |
| Embedding Model | all-MiniLM-L6-v2 (33 MB) |
| Torch | CPU-only wheel |
| Max PDF size | Limited by available RAM |
| Vector search K | 3 results (configurable) |

---

## � Security & Future Improvements

### Current Security Architecture

This production deployment uses industry-standard practices:

- ✅ **Secrets Management:** GitHub repository secrets for Azure credentials and ACR credentials
- ✅ **Network Isolation:** Azure Container Apps runs in a managed environment with ingress control
- ✅ **Service Principal:** Deployment uses an Azure AD service principal (not admin account)
- ✅ **API Validation:** FastAPI validates all request schemas with Pydantic

### Known Limitations & Planned Improvements

#### 1. ACR Authentication (Priority: Medium)

**Current approach:** Admin username/password stored in GitHub Secrets

```yaml
# Current (less secure, but stable)
username: ${{ secrets.ACR_USERNAME }}
password: ${{ secrets.ACR_PASSWORD }}
```

**Limitation:** Credentials are long-lived and stored as plaintext secrets.

**Recommended improvement:** **OIDC Federated Authentication**

Migrate to short-lived credential exchange between GitHub Actions and Azure using OpenID Connect:

```yaml
# Future (more secure)
- uses: azure/login@v2
  with:
    client-id: ${{ secrets.AZURE_CLIENT_ID }}
    tenant-id: ${{ secrets.AZURE_TENANT_ID }}
    subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
```

**Benefits:**
- No stored credentials to rotate
- Automatic token expiration (short-lived)
- Audit trail via Azure AD
- GitHub Actions natively supported

**How to implement (future):**
1. Create an Azure Entra ID application
2. Configure federated credential for GitHub repo
3. Store client ID, tenant ID, and subscription ID as secrets
4. Update `.github/workflows/deploy.yml` to use `azure/login@v2` with OIDC
5. Remove `AZURE_CREDENTIALS` secret

**Resources:**
- [GitHub OIDC in Azure](https://learn.microsoft.com/en-us/azure/active-directory/workload-identities/workload-identity-federation)
- [Azure/login@v2 OIDC support](https://github.com/azure/login#github-oidc-token-generation)

#### 2. Additional Enhancements

- [ ] **Persistent ephemeral uploads:** Optionally persist uploaded PDFs to Blob Storage
- [ ] **API Authentication:** Add optional API key or Bearer token validation to `/query` and `/upload`
- [ ] **Rate Limiting:** Implement rate limits to prevent abuse
- [ ] **Observability:** Add Application Insights for monitoring and diagnostics
- [ ] **Data Encryption:** Enable encryption for Blob Storage (already encrypted at rest by default)
- [ ] **Multi-region deployment:** Replicate to multiple Azure regions for HA

---

## �🛣️ Roadmap

- [ ] Add LLM endpoint for final answer synthesis
- [ ] Support multiple file formats (DOCX, TXT, etc.)
- [ ] Add authentication (API keys)
- [ ] Implement caching layer
- [ ] Support external vector database (Pinecone, Weaviate)
- [ ] Add monitoring and logging (Azure Application Insights)
- [ ] Document MCP client integration examples

---

## 📝 License

This project is provided as-is for educational and commercial purposes.

---

## 👤 Author

Created and deployed with GitHub Copilot assistance.

**Project Status:** ✅ Production-Ready (deployed on Azure Container Apps)

```yaml
- name: Azure login
  uses: azure/login@v2
  with:
    creds: ${{ secrets.AZURE_CREDENTIALS }}
```

### Manual Azure login

```bash
az login
az account set --subscription "<subscription-id>"
```

### Manual Container Apps deployment

```bash
chmod +x scripts/deploy-aca.sh
./scripts/deploy-aca.sh
```

The script creates or updates the Azure resources needed for the containerized app.

## Notes

- The system returns only retrieved context; it does not generate the final answer in the API.
- The retrieval layer is intentionally lightweight and designed for a limited budget and modest local hardware.
- For production use, add a real document ingestion source and a proper external LLM client if you want final answer synthesis outside this API.

## Requirements

Production dependencies are pinned in [requirements.txt](requirements.txt).

## License

This project is intended for internal or small enterprise deployment patterns and can be adapted to your environment and compliance needs.
