# O.M. Health AI — Medical RAG Assistant

A production-ready **AI-powered medical assistant** built on a full-stack RAG (Retrieval-Augmented Generation) architecture. The backend runs on **Azure Container Apps**, the frontend is deployed on **Vercel**. Designed for reliability, security, and a polished end-user experience.

**Live demo:** `https://rag-mcp-azure.redsand-f0795bb6.francecentral.azurecontainerapps.io`

---

## 🎯 Project Overview

**What it does:**
- Answers medical questions in natural language using the **MedQuAD** dataset (16,000+ validated Q&A pairs from the NIH)
- Retrieves the most relevant medical context from a FAISS vector index using **MMR search** (Maximal Marginal Relevance)
- Synthesizes a clear, professional answer via **Claude Haiku** (Anthropic) through OpenRouter — entirely server-side
- Exposes a clean chat UI with dark mode, suggestion chips, and Markdown rendering
- Also exposes a **MCP (Model Context Protocol)** endpoint for agentic AI integrations

**Architecture philosophy:**
- **Security by design:** the LLM API key never reaches the browser — all synthesis happens in the backend
- **Privacy by design:** zero client-side storage of sensitive data, stateless request processing
- **Lightweight:** CPU-only, no GPU, no heavy vector database — optimized for cost-effective cloud deployment
- **Production-ready:** automated CI/CD, tested endpoints, verified MCP integration

---

## 📊 Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| **Backend framework** | FastAPI + Uvicorn | Async HTTP, Pydantic validation |
| **RAG engine** | LangChain + FAISS | MMR search, in-memory vector store |
| **Embeddings** | HuggingFace `all-MiniLM-L6-v2` | CPU-optimized, 33 MB |
| **LLM** | Claude Haiku 4.5 via OpenRouter | Called server-side only |
| **HTTP client** | httpx | Async OpenRouter calls from backend |
| **Knowledge base** | MedQuAD dataset (NIH) | 16,000+ medical Q&A pairs, pre-built FAISS index |
| **Document storage** | Azure Blob Storage | Source of truth for index files in production |
| **MCP server** | MCP SDK v2, Streamable HTTP | Agentic tool interface for external AI agents |
| **Containerization** | Docker | `python:3.12-slim`, CPU-only torch wheel |
| **Backend hosting** | Azure Container Apps | Serverless, auto-scaling, managed ingress |
| **Container registry** | Azure Container Registry (ACR) | Image storage |
| **Frontend hosting** | Vercel | Static HTML/CSS/JS, global CDN |
| **CI/CD** | GitHub Actions | Test → build → push → deploy, idempotent |

---

## 🏛️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER BROWSER                             │
│              frontend/ (HTML + CSS + JS)                        │
│              Hosted on Vercel (static)                          │
└──────────────────────────┬──────────────────────────────────────┘
                           │  POST /chat  { query }
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              AZURE CONTAINER APPS (Backend)                     │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  FastAPI  app/main.py                                   │   │
│  │                                                         │   │
│  │  POST /chat ──► rag_engine.search() (MMR, k=3)         │   │
│  │                        │                               │   │
│  │                        ▼                               │   │
│  │              FAISS index (in-memory)                   │   │
│  │              MedQuAD Q&A embeddings                    │   │
│  │                        │                               │   │
│  │                        ▼                               │   │
│  │         httpx ──► OpenRouter API                       │   │
│  │                  Claude Haiku 4.5                      │   │
│  │                  (OPENROUTER_API_KEY — secret Azure)   │   │
│  │                        │                               │   │
│  │                        ▼                               │   │
│  │              { "answer": "..." }                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Also exposes: /query (raw context), /reindex, /upload, /mcp   │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
              Azure Blob Storage
              (FAISS index files: index.faiss + index.pkl)
```

**Key security boundary:** the `OPENROUTER_API_KEY` is stored as an Azure Container Apps secret and injected at runtime. It is never sent to the browser, never committed to source, and never logged.

---

## 🏗️ Project Structure

```
rag-mcp-azure/
├── app/
│   ├── data/                    # PDF fallback for local dev
│   ├── main.py                  # FastAPI app: /chat, /query, /reindex, /upload, MCP mount
│   └── rag_engine.py            # RAG pipeline: MMR search, Blob/local ingestion, FAISS
├── frontend/
│   ├── index.html               # Full-page UI: navbar, hero, chat card, features, FAQ
│   ├── style.css                # Design system: CSS variables, dark mode, responsive
│   └── app.js                   # Chat logic: POST /chat, Markdown rendering, dark mode toggle
├── medquad_index/
│   ├── index.faiss              # Pre-built FAISS index (MedQuAD)
│   └── index.pkl                # Embedding metadata
├── scripts/
│   ├── build_index_offline.py   # Build FAISS index from medquad.csv locally
│   ├── upload_index_to_blob.py  # Upload index files to Azure Blob Storage
│   └── deploy-aca.sh            # Manual Azure deployment script
├── tests/
│   ├── test_api.py              # REST endpoint tests (CI)
│   └── test_mcp_integration.py  # MCP client tests (manual, live server)
├── .github/workflows/deploy.yml # CI/CD pipeline
├── medquad.csv                  # Source dataset (NIH MedQuAD)
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## 🧠 RAG Engine — Key Design Decisions

### Dataset: MedQuAD

The knowledge base is built from the **MedQuAD** (Medical Question Answering Dataset) published by the NIH. It contains over 16,000 question-answer pairs covering diseases, symptoms, treatments, and diagnostics across dozens of medical specialties.

Unlike a pure document ingestion pipeline, the FAISS index here embeds **both the question and the answer text**, giving the retrieval step richer semantic context to match against user queries.

### MMR Search (Maximal Marginal Relevance)

The `search()` method in `rag_engine.py` uses **MMR** instead of plain cosine similarity:

```python
results = self.vector_store.max_marginal_relevance_search(query, k=3, fetch_k=20)
```

- `fetch_k=20`: retrieve the top 20 candidates by similarity
- `k=3`: from those 20, select the 3 most **diverse** results

This prevents the top-3 results from being near-duplicate chunks (a common failure mode when multiple similar Q&A pairs exist in the dataset), and ensures the LLM receives varied, complementary context.

### Pre-built Index Loading

In production, the FAISS index is **pre-built offline** from `medquad.csv` and stored in Azure Blob Storage (`INDEX_CONTAINER_NAME`). On startup, the engine downloads `index.faiss` + `index.pkl` directly — no re-embedding at boot time, which keeps cold start under 30 seconds on 0.5 CPU.

---

## 🔐 Security Architecture

### API Key — Server-Side Only

The most important security change from the initial prototype: **the OpenRouter API key never leaves the server.**

| | Old architecture | Current architecture |
|---|---|---|
| Who calls OpenRouter? | Browser (JavaScript) | Backend (Python/httpx) |
| Where is the key? | `sessionStorage` (client) | Azure Container Apps secret |
| Key visible in DevTools? | ✅ Yes | ❌ No |
| Key in source code? | Risk | Never — `os.getenv()` only |

The key is injected at deploy time:

```powershell
az containerapp secret set --name rag-mcp-azure --resource-group rg-rag-mcp-azure `
  --secrets "openrouter-api-key=sk-or-v1-..."

az containerapp update --name rag-mcp-azure --resource-group rg-rag-mcp-azure `
  --set-env-vars "OPENROUTER_API_KEY=secretref:openrouter-api-key"
```

### Full Security Checklist

- ✅ **OPENROUTER_API_KEY** — Azure Container Apps secret, never in source or env plaintext
- ✅ **BLOB_CONNECTION_STRING** — Azure Container Apps secret, re-applied on every CI deploy
- ✅ **GitHub Secrets** — Azure, ACR, and Blob credentials stored as Actions secrets
- ✅ **Service Principal** — deployment uses a scoped Azure AD SP, not the subscription owner
- ✅ **Pydantic validation** — all request bodies validated before processing
- ✅ **MCP DNS rebinding protection** — `TransportSecuritySettings` scoped to known hosts
- ✅ **CORS** — open for public demo (MedQuAD is public data); restrict for production use
- ✅ **Key rotation practiced** — Blob Storage key was rotated after accidental log exposure during early debugging

---

## 🖥️ Frontend — UI/UX

The frontend is a **static single-page application** (HTML + CSS + JS, no framework) deployed on Vercel.

### Features

- **Full-page layout** — navbar, hero section (2-column: pitch + live chat), features grid, security section, FAQ
- **Functional chat card** — real-time POST to `/chat`, typing indicator, timestamped messages
- **Markdown rendering** — bot responses rendered with headers, bold, lists, blockquotes (custom lightweight parser, no library)
- **Lucide Icons** — SVG icon library replacing all native emojis for consistent cross-platform rendering
- **Dark mode** — toggled via a settings dropdown in the navbar, persisted in `localStorage`, applied via `body[data-theme="dark"]` CSS variable overrides with smooth transition
- **Suggestion chips** — pre-filled question shortcuts that disappear after first use
- **Privacy by design** — zero `sessionStorage`/`localStorage` usage for sensitive data; no API key ever stored client-side

### Dark Mode Implementation

```css
/* Light (default) */
:root {
    --bg-color: #fdfdfd;
    --text-main: #111827;
    --white: #ffffff;
    --bot-bg: #f3f4f6;
    /* ... */
}

/* Dark */
body[data-theme="dark"] {
    --bg-color: #111827;
    --text-main: #f3f4f6;
    --white: #1f2937;
    --bot-bg: #374151;
    /* ... */
}
```

All colors in `style.css` use CSS variables — no hardcoded hex values for interface elements — ensuring the dark mode applies globally and consistently.

---

## 📡 API Endpoints

### POST /chat ⭐ Primary endpoint
Full RAG + LLM pipeline. Retrieves context from FAISS, calls Claude Haiku via OpenRouter server-side, returns a synthesized medical answer.

**Request:**
```json
{ "query": "What are the symptoms of hypertension?" }
```

**Response:**
```json
{ "answer": "Hypertension is often called the 'silent killer' because..." }
```

### POST /query
Returns raw FAISS context chunks without LLM synthesis. Used internally and for debugging/testing.

**Response:**
```json
{
  "query": "...",
  "context_extrait": "Extrait 1:\n...\n\nExtrait 2:\n..."
}
```

### GET /health
```json
{ "status": "ok" }
```

### POST /reindex
Rebuilds the FAISS index from Blob Storage (or local files). Call after uploading new documents.

### POST /upload
Uploads a PDF and adds it to the in-memory index (ephemeral — lost on restart or `/reindex`).

### MCP `/mcp-server/mcp`
See [MCP Protocol Integration](#-mcp-protocol-integration) below.

---

## 🔌 MCP Protocol Integration

**Model Context Protocol (MCP)** is an open standard for connecting AI agents to external tools. O.M. Health AI exposes a `search_documents` tool over **Streamable HTTP**, allowing any MCP-compatible agent (Claude Desktop, custom agents) to query the medical knowledge base directly.

### Endpoint

| Environment | URL |
|---|---|
| Local | `http://localhost:8000/mcp-server/mcp` |
| Production | `https://rag-mcp-azure.redsand-f0795bb6.francecentral.azurecontainerapps.io/mcp-server/mcp` |

### Exposed Tool

| Tool | Input | Output |
|------|-------|--------|
| `search_documents` | `query: string` | Top-3 MMR-ranked medical context chunks |

### Python client example (verified end-to-end)

```python
import asyncio
from mcp.client.streamable_http import streamable_http_client
from mcp import ClientSession

async def main():
    url = "https://rag-mcp-azure.redsand-f0795bb6.francecentral.azurecontainerapps.io/mcp-server/mcp"
    async with streamable_http_client(url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("search_documents", {"query": "symptoms of diabetes"})
            for content in result.content:
                if hasattr(content, "text"):
                    print(content.text)

asyncio.run(main())
```

### Claude Desktop config

```json
{
  "mcpServers": {
    "om-health-ai": {
      "url": "https://rag-mcp-azure.redsand-f0795bb6.francecentral.azurecontainerapps.io/mcp-server/mcp"
    }
  }
}
```

### DNS Rebinding Protection

The MCP SDK restricts the `Host` header to `localhost` by default. `TransportSecuritySettings` in `app/main.py` explicitly allow-lists the production Azure hostname — without this, requests return `421 Misdirected Request`.

---

## 🚀 Quick Start

### Local Development

```bash
git clone https://github.com/oumniya03/rag-mcp-azure.git
cd rag-mcp-azure
python -m venv .venv
.venv\Scripts\Activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

Set environment variables (create a `.env` or export directly):

```bash
# Required for LLM synthesis
export OPENROUTER_API_KEY=sk-or-v1-...

# Optional: load FAISS index from Blob Storage instead of local medquad_index/
export INDEX_CONTAINER_NAME=medquad-index
export BLOB_CONTAINER_URL=<your-connection-string>
```

Run the backend:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open `frontend/index.html` directly in a browser, or serve it locally:

```bash
cd frontend && python -m http.server 3000
```

Test the chat endpoint:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the symptoms of high blood pressure?"}'
```

---

## 🐳 Docker

```bash
# Build
docker build -t om-health-ai:latest .

# Run (pass the API key at runtime)
docker run --rm -p 8000:8000 \
  -e OPENROUTER_API_KEY=sk-or-v1-... \
  om-health-ai:latest
```

**Image profile:** `python:3.12-slim` base, CPU-only torch wheel, ~500 MB compressed on ACR.

---

## ☁️ Azure Deployment

### Production Resources

| Resource | Name | Notes |
|---|---|---|
| Container App | `rag-mcp-azure` | Backend API |
| Resource Group | `rg-rag-mcp-azure` | France Central |
| ACA Environment | `cae-rag-mcp-azure` | Shared environment |
| ACR | `ragmcpacr26` | Docker image registry |
| Blob Storage | `ragmcpstorage26` | FAISS index + source PDFs |
| Compute | 0.5 CPU / 1.0 Gi | Sufficient for CPU-only inference |

### Required GitHub Secrets

| Secret | Description |
|--------|-------------|
| `AZURE_CREDENTIALS` | Service principal JSON (`az ad sp create-for-rbac --sdk-auth`) |
| `ACR_USERNAME` | ACR admin username |
| `ACR_PASSWORD` | ACR admin password |
| `BLOB_CONNECTION_STRING` | Blob Storage connection string (re-applied as Container App secret on every deploy) |
| `OPENROUTER_API_KEY` | OpenRouter API key (applied as Container App secret) |

### CI/CD Pipeline (`.github/workflows/deploy.yml`)

On every push to `main`:

1. Install dependencies
2. Run REST tests (`pytest tests/ -v -m "not integration"`)
3. Login to Azure (service principal)
4. Build & push Docker image to ACR
5. Idempotent deploy: `az containerapp update` if exists, `az containerapp create` otherwise
6. Re-apply both secrets (`blob-connection-string`, `openrouter-api-key`) on every deploy

```bash
git push origin main  # triggers the full pipeline
```

### Blob Storage — FAISS Index

The pre-built FAISS index is stored in Blob Storage and loaded at startup (no re-embedding on cold start):

```powershell
# Upload index files
az storage blob upload-batch `
  --destination medquad-index `
  --source medquad_index/ `
  --account-name ragmcpstorage26 `
  --auth-mode key

# Set the index container env var
az containerapp update --name rag-mcp-azure --resource-group rg-rag-mcp-azure `
  --set-env-vars "INDEX_CONTAINER_NAME=medquad-index"
```

---

## 🧪 Testing

### Automated (CI)

```bash
pytest tests/ -v -m "not integration"
```

Covers `/health`, `/query`, `/reindex`, `/upload` — runs on every push to `main`.

### MCP Integration (manual, requires live server)

```bash
pytest tests/test_mcp_integration.py -v

# Against local instance:
$env:MCP_TEST_URL="http://localhost:8000/mcp-server/mcp"
pytest tests/test_mcp_integration.py -v
```

### Quick production smoke test

```powershell
# Health
Invoke-RestMethod -Uri "https://rag-mcp-azure.redsand-f0795bb6.francecentral.azurecontainerapps.io/health"

# Chat
$body = @{query="What is hypertension?"} | ConvertTo-Json
Invoke-RestMethod -Method Post `
  -Uri "https://rag-mcp-azure.redsand-f0795bb6.francecentral.azurecontainerapps.io/chat" `
  -ContentType "application/json" -Body $body
```

---

## 🔧 Configuration Reference

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | Yes (production) | LLM API key — Azure secret, never plaintext |
| `BLOB_CONTAINER_URL` | No | Blob Storage connection string for PDF ingestion |
| `INDEX_CONTAINER_NAME` | No | Blob container name for pre-built FAISS index |

**Local tweaks** (`app/rag_engine.py`):
- `chunk_size` / `chunk_overlap` — text splitter parameters (default: 500 / 50)
- `k` / `fetch_k` — MMR search parameters (default: k=3, fetch_k=20)
- Embedding model — `HuggingFaceEmbeddings(model_name=...)`

---

## ⚙️ Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `/chat` returns config error | `OPENROUTER_API_KEY` not set | Set the Azure Container App secret |
| Empty context from `/query` | No index loaded | Check startup logs for `Base vectorielle prête !`, call `/reindex` |
| MCP `421 Misdirected Request` | Host not in allow-list | Add host to `TransportSecuritySettings` in `main.py` |
| MCP `500 Task group not initialized` | MCP not started via `lifespan` | Ensure `async with mcp.session_manager.run()` is in the lifespan context |
| Docker build fails | Dependency conflict | Check Python 3.12 compatibility in `requirements.txt` |
| GitHub Actions fails | Missing secrets | Verify all 5 secrets are set in repository settings |

---

## 📈 Performance Profile

| Metric | Value |
|--------|-------|
| Deployment CPU | 0.5 vCPU |
| Deployment Memory | 1.0 Gi |
| Embedding model | `all-MiniLM-L6-v2` (33 MB, CPU) |
| Cold start | ~25–30s (index download + model load) |
| Inference | CPU-only, no GPU |
| FAISS search | MMR, k=3 from fetch_k=20 |
| LLM | Claude Haiku 4.5, temp=0.3, max_tokens=1000 |

---

## 🛣️ Roadmap

- [x] MedQuAD medical knowledge base
- [x] MMR search for diverse, non-redundant context
- [x] Server-side LLM synthesis (`/chat` endpoint)
- [x] API key security — backend-only, Azure secret
- [x] Full-page frontend with dark mode and Lucide icons
- [x] MCP Streamable HTTP endpoint (verified end-to-end)
- [x] Pre-built FAISS index loaded from Blob Storage
- [x] Automated CI/CD with GitHub Actions
- [ ] OIDC federated auth for CI/CD (replace ACR admin credentials)
- [ ] Rate limiting on `/chat`
- [ ] API key authentication for `/chat` and `/upload`
- [ ] Azure Application Insights (latency, error rate, usage)
- [ ] Persist `/upload` documents to Blob Storage
- [ ] Multi-language support

---

## 📝 License

Provided as-is for educational and portfolio purposes.

---

## 👤 Author

**Oumniya Moutaouakil** — AI Engineer, LLM / Agentic AI & RAG Systems.

**Project status:** ✅ Production-ready — backend on Azure Container Apps, frontend on Vercel, REST + MCP endpoints verified end-to-end.
