# RAG MCP Azure - Lightweight Retrieval-Augmented Generation Service

A production-ready **Retrieval-Augmented Generation (RAG)** API deployed on **Azure Container Apps**. Built for efficiency with a CPU-only footprint, in-memory vector storage, Azure Blob Storage ingestion, and full MCP protocol compatibility — verified end-to-end.

---

## 🎯 Project Overview

**What it does:**
- Ingests PDF documents from Azure Blob Storage (with local folder fallback for development)
- Chunks and embeds them using sentence transformers
- Stores embeddings in FAISS (in-memory vector store)
- Serves FastAPI HTTP endpoints for document retrieval, reindexing, and ad-hoc PDF upload
- Exposes a real, tested MCP (Model Context Protocol) server over Streamable HTTP
- Returns only relevant document context (no final LLM synthesis — kept client-side by design)

**Design philosophy:**
- Lightweight: Optimized for 8 GB RAM, CPU-only environments
- Serverless: Deployed on Azure Container Apps (auto-scaling, managed infrastructure)
- Cost-effective: No heavy vector databases or GPU requirements
- Production-ready: Automated CI/CD with GitHub Actions, tested REST endpoints, and a verified MCP integration

---

## 📊 Tech Stack

| Component | Technology | Notes |
|-----------|-----------|-------|
| **Framework** | FastAPI + Uvicorn | Async HTTP server |
| **RAG Engine** | LangChain + FAISS | PDF loading, text splitting, embeddings, vector search |
| **Embeddings** | HuggingFace Sentence Transformers | CPU-optimized models (all-MiniLM-L6-v2) |
| **Document Storage** | Azure Blob Storage | Source of truth for PDFs in production |
| **MCP Server** | MCP SDK v2 (mcp.server.mcpserver), Streamable HTTP transport | Real, tested tool interface for agentic retrieval |
| **Containerization** | Docker | CPU-optimized image (Python 3.12-slim, no GPU torch) |
| **Orchestration** | Azure Container Apps | Managed, auto-scaling, ingress |
| **Container Registry** | Azure Container Registry (ACR) | Image storage and management |
| **CI/CD** | GitHub Actions | Automated tests, build, push, and idempotent deploy |

---

## 🏗️ Project Structure

```
rag-mcp-azure/
├── app/
│   ├── data/                    # PDF documents for local dev (fallback)
│   │   └── *.pdf
│   ├── main.py                  # FastAPI app + MCP server (mount, lifespan, security)
│   └── rag_engine.py            # RAG logic (Blob/local ingestion, chunking, search)
├── tests/
│   ├── test_api.py              # REST endpoint tests (run in CI)
│   └── test_mcp_integration.py  # Real MCP client tests (manual, live server required)
├── .github/
│   └── workflows/
│       └── deploy.yml           # GitHub Actions CI/CD pipeline
├── scripts/
│   └── deploy-aca.sh            # Manual Azure deployment script
├── Dockerfile                    # Production image definition
├── .dockerignore
├── .gitignore
├── pytest.ini                    # Test markers and asyncio config
├── requirements.txt
└── README.md
```

---

## 🔌 MCP Protocol Integration

### What is MCP?

**Model Context Protocol (MCP)** is an open standard for connecting AI agents to external tools and data sources. Instead of embedding knowledge retrieval inside an LLM, MCP exposes it as a **discoverable tool** that any compatible agent (Claude, Gemini, custom LLMs) can invoke over a standard transport.

**Key advantage for interviews:** Demonstrates a real, working implementation of an emerging agentic AI standard, verified end-to-end with the official MCP client SDK — not just a REST API with an MCP label attached.

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

A plain `curl` GET request to the MCP endpoint returns a `400 Bad Request` with a JSON-RPC error:

```json
{"jsonrpc":"2.0","id":null,"error":{"code":-32600,"message":"Bad Request: Missing session ID"}}
```

**This is expected, not a bug.** MCP over Streamable HTTP requires a session handshake before any tool call — `curl` alone doesn't perform this. This response confirms the server correctly speaks the MCP JSON-RPC protocol; it's just rejecting an incomplete request. A real MCP client handles this handshake automatically.

### DNS Rebinding Protection

The MCP Python SDK enables DNS rebinding protection by default, restricting the `Host` header to `localhost`/`127.0.0.1` unless explicitly configured otherwise. Since this server is deployed on a public Azure domain, `TransportSecuritySettings` is configured in `app/main.py` to explicitly allow both local development hosts and the production Azure Container Apps hostname:

```python
security_settings = TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=[
        "127.0.0.1:*", "localhost:*", "[::1]:*",
        "rag-mcp-azure.redsand-f0795bb6.francecentral.azurecontainerapps.io",
    ],
    allowed_origins=[
        "http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*",
        "https://rag-mcp-azure.redsand-f0795bb6.francecentral.azurecontainerapps.io",
    ],
)
```

Without this, requests to the production URL fail with `421 Misdirected Request: Invalid Host header` — the protection is working correctly, it just needs the production host explicitly allow-listed.

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

**Python MCP client** — verified working end-to-end against production:

```python
import asyncio
from mcp.client.streamable_http import streamable_http_client
from mcp import ClientSession

async def test_search():
    url = "https://rag-mcp-azure.redsand-f0795bb6.francecentral.azurecontainerapps.io/mcp-server/mcp"
    async with streamable_http_client(url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print(f"Available tools: {[t.name for t in tools.tools]}")
            result = await session.call_tool(
                "search_documents", {"query": "durée maximale contrat intérimaire"}
            )
            for content in result.content:
                if hasattr(content, "text"):
                    print(content.text)

asyncio.run(test_search())
```

Sample output:
```
Available tools: ['search_documents']
Extrait 1:
Article 26
§1er. Par poste de travail, pas plus de trois tentatives, de maximum six mois par intérimaire...
```

### Automated Integration Testing

`tests/test_mcp_integration.py` contains automated tests using the same client flow, marked with `@pytest.mark.integration` and excluded from the CI pipeline (since they require a live deployed server and shouldn't run against a service mid-deployment). Run them manually with:

```bash
pytest tests/test_mcp_integration.py -v
```

Or against a local instance:
```powershell
$env:MCP_TEST_URL="http://localhost:8000/mcp-server/mcp"
pytest tests/test_mcp_integration.py -v
```

### Known limitation

The MCP mount path (`/mcp-server/mcp`) is a workaround for a routing conflict between the MCP SDK's internal `/mcp` route and FastAPI's REST routes at root level. A cleaner path structure is a possible future improvement, but the current setup is fully functional and tested end-to-end.

---

## 🚀 Quick Start

### Local Development

**1. Clone and setup:**
```bash
git clone https://github.com/oumniya03/rag-mcp-azure.git
cd rag-mcp-azure
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate
pip install -r requirements.txt
```

**2. Add PDF documents (local dev fallback, used when `BLOB_CONTAINER_URL` is not set):**
```bash
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

This service ingests documents from **Azure Blob Storage** in production. This is the recommended approach — PDFs live outside the Docker image, so the knowledge base can be updated without a rebuild.

### Architecture

```
┌──────────────────────────────────────┐
│   Azure Blob Storage (documents/)    │
│   - travail_interimaire.pdf          │
└──────────────────┬───────────────────┘
                    │
                    ▼
        ┌──────────────────────┐
        │  RAG Engine          │
        │ (rag_engine.py)      │
        │ - Download to temp   │
        │   file (PyPDFLoader  │
        │   needs a real path) │
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
        │  /query, /reindex,   │
        │  /upload             │
        └──────────────────────┘
```

### Setup Instructions

**1. Create a storage account and container:**

```powershell
az storage account create --name ragmcpstorage26 --resource-group rg-rag-mcp-azure --location francecentral --sku Standard_LRS
az storage container create --name documents --account-name ragmcpstorage26 --auth-mode login
```

> The container name is hardcoded as `"documents"` in `rag_engine.py` — keep this name or update the code if you change it.

**2. Upload PDF files:**

```powershell
az storage blob upload-batch --destination documents --source app/data --account-name ragmcpstorage26 --auth-mode key
```

**3. Store the connection string as a Container App secret (not a plaintext env var):**

```powershell
$connString = az storage account show-connection-string --name ragmcpstorage26 --resource-group rg-rag-mcp-azure --query connectionString -o tsv

az containerapp secret set --name rag-mcp-azure --resource-group rg-rag-mcp-azure --secrets "blob-connection-string=$connString"

az containerapp update --name rag-mcp-azure --resource-group rg-rag-mcp-azure --set-env-vars "BLOB_CONTAINER_URL=secretref:blob-connection-string"
```

> **Important:** this configuration is also codified in `.github/workflows/deploy.yml` (see below) so it persists across every automated deployment — setting it manually alone would be overwritten by the next `git push`.

**4. Trigger reindexing after adding new PDFs:**

```bash
curl -X POST https://rag-mcp-azure.redsand-f0795bb6.francecentral.azurecontainerapps.io/reindex
# Response: {"status": "Réindexation réussie."}
```

### How it Works

- **On startup:** If `BLOB_CONTAINER_URL` is set, the service downloads all PDFs from the `documents` container in Blob Storage to temporary files (`PyPDFLoader` requires a real file path, not an in-memory stream) and indexes them. Otherwise, it falls back to the local `app/data/` folder.
- **On `/reindex` call:** The service re-downloads all documents from Blob Storage and rebuilds the FAISS index from scratch.
- **Ephemeral uploads:** Documents uploaded via `/upload` are added to the in-memory index only — they are **not** persisted to Blob Storage and will be lost on restart or on the next `/reindex` call (which rebuilds from Blob Storage/local files only).

### A real debugging lesson: `BytesIO` vs `PyPDFLoader`

An early version of this integration passed downloaded blob bytes directly to `PyPDFLoader(BytesIO(blob_data))`, which fails silently with `File path <_io.BytesIO object> is not a valid file or url` — `PyPDFLoader` requires an actual file path. The fix: write blob bytes to a `tempfile.NamedTemporaryFile` first, then load from that path, deleting it afterward. This is implemented in `rag_engine.py`.

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
- **Blob Storage:** `ragmcpstorage26` (container: `documents`)
- **Compute:** 0.5 CPU, 1.0 Gi memory

### GitHub Secrets (Required)

Set these in your GitHub repository settings (Settings → Secrets and variables → Actions):

| Secret | Description |
|--------|-------------|
| `AZURE_CREDENTIALS` | Service principal JSON (from `az ad sp create-for-rbac --sdk-auth`) |
| `ACR_USERNAME` | ACR admin username (from `az acr credential show`) |
| `ACR_PASSWORD` | ACR admin password (from `az acr credential show`) |
| `BLOB_CONNECTION_STRING` | Azure Blob Storage connection string, re-applied as a Container App secret on every deploy |

### Deployment Pipeline

The workflow [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml) runs on every push to `main`:

1. **Checkout code**
2. **Python setup** (3.12) and dependency install
3. **Run tests** (`pytest tests/ -v -m "not integration"` — REST endpoint tests only; MCP integration tests are excluded since they require a live server)
4. **Azure login** (service principal)
5. **Docker Buildx setup**, login to ACR, build & push image
6. **Verify** the Container Apps environment exists
7. **Deploy:** if the Container App already exists, `az containerapp secret set` (refreshing the Blob Storage secret) followed by `az containerapp update`; otherwise `az containerapp create` with the secret and image set from scratch — this idempotent logic prevents accidentally wiping the app's configuration on redeploy

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

```bash
curl -X POST http://localhost:8000/reindex
# Response: {"status": "Réindexation réussie."}
```

**Use case:** After uploading new PDFs to Blob Storage, call this endpoint to update the search index without restarting the service.

### POST /upload
Upload a PDF document and add it to the RAG index (ephemeral, in-memory only).

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

**Important:** Uploaded documents are lost on restart or on the next `/reindex` call. To persist documents permanently, upload them directly to Blob Storage instead.

### MCP Endpoint (`/mcp-server/mcp`)
See the [MCP Protocol Integration](#-mcp-protocol-integration) section above.

---

## 🔧 Configuration

### Environment variables
- `BLOB_CONTAINER_URL` (optional): Azure Blob Storage connection string. If set, documents load from the `documents` Blob container instead of local files. In production this is injected via a Container App secret reference, never as plaintext.

### Local tweaking
Edit `app/rag_engine.py` to customize:
- `DATA_DIR`: local PDF fallback folder
- `chunk_size` / `chunk_overlap`: passed to `RecursiveCharacterTextSplitter` (default: 500 / 50)
- `k`: number of results returned by `search()` (default: 3)
- Embedding model: change the `HuggingFaceEmbeddings` model name

---

## 📖 Key Files Explained

### app/main.py
- FastAPI application with four REST endpoints (`/health`, `/query`, `/reindex`, `/upload`)
- MCP server (Streamable HTTP) mounted at `/mcp-server/mcp`, exposing the `search_documents` tool
- FastAPI `lifespan` manages the MCP session manager's async lifecycle (required — without it, MCP requests fail with `RuntimeError: Task group is not initialized`)
- `TransportSecuritySettings` configured to allow the production Azure host (DNS rebinding protection)

### app/rag_engine.py
- `SimpleRAGEngine` class: orchestrates the RAG pipeline
- `initialize_store()`: loads PDFs from Blob Storage or local folder, chunks, embeds, indexes
- `_load_documents_from_blob()`: downloads blobs to temp files before parsing (see PyPDFLoader note above)
- `add_documents_from_bytes()`: powers `/upload` (ephemeral, in-memory only)
- `ingest()`: powers `/reindex`
- `search()`: FAISS similarity search, returns raw context (no LLM synthesis)

### Dockerfile
- CPU-only PyTorch wheel (no CUDA libraries)
- Minimal layer footprint, `python:3.12.8-slim` base
- Runs as non-root user

### .github/workflows/deploy.yml
- Runs REST tests, builds and pushes the Docker image, deploys idempotently to Azure Container Apps
- Re-applies the Blob Storage secret on every deploy so it survives redeployment

---

## 🧪 Testing

### Automated tests (CI)
```bash
pytest tests/ -v -m "not integration"
```
15 tests covering `/health`, `/query`, `/reindex`, `/upload` — runs automatically in GitHub Actions on every push to `main`.

### MCP integration tests (manual, requires a live server)
```bash
pytest tests/test_mcp_integration.py -v
```
3 tests using the real MCP client SDK: session handshake, tool discovery, and tool invocation — run against production by default (override with the `MCP_TEST_URL` environment variable).

### Production endpoint test (PowerShell)
```powershell
Invoke-RestMethod -Uri "https://rag-mcp-azure.redsand-f0795bb6.francecentral.azurecontainerapps.io/health"

$body = @{query="test"} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "https://rag-mcp-azure.redsand-f0795bb6.francecentral.azurecontainerapps.io/query" -ContentType "application/json" -Body $body
```

> **PowerShell note:** `Invoke-RestMethod`/`Invoke-WebRequest` sometimes mis-encode accented characters (é, è) typed directly in a query string, showing mojibake like `durÃ©e` in the terminal. This is a display artifact of PowerShell 5.1, not a server-side bug — the API itself handles UTF-8 correctly (verified against production).

---

## 🔐 Azure Prerequisites (First-time setup)

### 1. Register required providers (one-time)
```bash
az provider register --namespace Microsoft.App --wait
az provider register --namespace Microsoft.ContainerRegistry --wait
az provider register --namespace Microsoft.Storage --wait
```

### 2. Create service principal
```bash
az ad sp create-for-rbac --name "rag-mcp-github" --role Contributor --sdk-auth
# Copy the JSON output → set as AZURE_CREDENTIALS secret in GitHub
```

### 3. Enable ACR admin account
```bash
az acr update --name ragmcpacr26 --admin-enabled true
az acr credential show --name ragmcpacr26
# Copy username/password → set as ACR_USERNAME, ACR_PASSWORD secrets in GitHub
```

### 4. Verify ACA environment
```bash
az containerapp env list -o table
# Should show: cae-rag-mcp-azure in rg-rag-mcp-azure, France Central
```

> **Note:** an Azure subscription can only have **one** global Container App Environment by default. Reuse the existing one rather than creating a new one — attempting to create a second will fail with `MaxNumberOfGlobalEnvironmentsInSubExceeded`.

---

## ⚙️ Troubleshooting

### Docker build fails
- Check `requirements.txt` for incompatible packages
- Ensure Python 3.12 compatibility
- Review Dockerfile for typos

### GitHub Actions workflow fails
- Check all four secrets are set in repository settings
- Verify ACR admin is enabled
- Run `az containerapp env show` locally to confirm the environment exists
- `az containerapp create` does **not** accept a `--location` parameter — location is inherited from the environment

### Blob Storage authentication errors (`401`, `MissingSubscriptionRegistration`)
- Ensure `Microsoft.Storage` provider is registered (see Prerequisites above)
- Blob upload via Azure CLI requires either `--auth-mode key` or an RBAC role like "Storage Blob Data Contributor" assigned to your account with `--auth-mode login`

### MCP endpoint returns `421 Misdirected Request`
- The production host isn't in `TransportSecuritySettings.allowed_hosts` — see the DNS Rebinding Protection section above

### MCP endpoint returns `500 Internal Server Error: Task group is not initialized`
- The MCP session manager wasn't started via FastAPI's `lifespan` — a plain `app.mount()` alone is not enough

### /query endpoint returns empty context
- Check that PDFs exist in Blob Storage (or `app/data/` for local fallback)
- Check startup logs for `Base vectorielle prête !`
- Try `/reindex` to force a rebuild

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

## 🔒 Security & Future Improvements

### Current Security Architecture

- ✅ **Secrets Management:** GitHub repository secrets for Azure, ACR, and Blob Storage credentials — never committed to source
- ✅ **Container App Secrets:** Blob Storage connection string stored as a Container App secret (`secretref`), not a plaintext environment variable
- ✅ **Network Isolation:** Azure Container Apps runs in a managed environment with ingress control
- ✅ **Service Principal:** Deployment uses an Azure AD service principal (not the subscription owner account)
- ✅ **API Validation:** FastAPI validates all request schemas with Pydantic
- ✅ **MCP DNS Rebinding Protection:** explicitly scoped to known hosts rather than disabled
- ✅ **Key rotation practiced:** the Blob Storage account key was rotated after being inadvertently exposed in application logs during initial debugging — a concrete lesson in why secrets should never be logged, even for troubleshooting

### Known Limitations & Planned Improvements

#### 1. ACR Authentication (Priority: Medium)

**Current approach:** Admin username/password stored in GitHub Secrets.

**Limitation:** Credentials are long-lived and stored as plaintext secrets.

**Recommended improvement:** Migrate to **OIDC Federated Authentication** between GitHub Actions and Azure — short-lived tokens, no stored credentials to rotate, native Azure AD audit trail.

```yaml
# Future
- uses: azure/login@v2
  with:
    client-id: ${{ secrets.AZURE_CLIENT_ID }}
    tenant-id: ${{ secrets.AZURE_TENANT_ID }}
    subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
```

**How to implement:**
1. Create an Azure Entra ID application
2. Configure federated credentials for this GitHub repo
3. Store client ID, tenant ID, subscription ID as secrets
4. Update `deploy.yml` to use OIDC-based `azure/login@v2`
5. Remove the `AZURE_CREDENTIALS` and ACR admin secrets

**Resources:** [GitHub OIDC in Azure](https://learn.microsoft.com/en-us/azure/active-directory/workload-identities/workload-identity-federation) · [azure/login OIDC support](https://github.com/azure/login#github-oidc-token-generation)

#### 2. Additional Enhancements

- [ ] Persist ephemeral `/upload` documents to Blob Storage instead of memory-only
- [ ] API authentication (API key or Bearer token) on `/query` and `/upload`
- [ ] Rate limiting
- [ ] Observability via Azure Application Insights (latency, error rate, request volume)
- [ ] Multi-region deployment for high availability

---

## 🛣️ Roadmap

- [x] Real MCP protocol support with end-to-end client verification
- [x] Azure Blob Storage document pipeline
- [x] Automated REST + MCP integration tests
- [ ] Add LLM endpoint for final answer synthesis
- [ ] Support multiple file formats (DOCX, TXT, etc.)
- [ ] API authentication
- [ ] OIDC federated auth for CI/CD
- [ ] Application Insights monitoring
- [ ] Support external vector database (Pinecone, Weaviate) for larger corpora

---

## 📝 License

This project is provided as-is for educational and portfolio purposes.

---

## 👤 Author

Oumniya Moutaouakil — AI Engineer, LLM/Agentic AI & RAG Systems.

**Project Status:** ✅ Production-Ready — deployed on Azure Container Apps, REST + MCP endpoints verified end-to-end against production.


