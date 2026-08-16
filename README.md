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

---

## 🔧 Configuration

### Environment variables (not required for local dev)
- None currently. All config is code-based in `main.py` and `rag_engine.py`.

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
- FastAPI application with two endpoints (`/health`, `/query`)
- MCP server initialization (search_documents tool)
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

## 🛣️ Roadmap

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
