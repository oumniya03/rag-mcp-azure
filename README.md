# RAG MCP Azure

A lightweight enterprise Retrieval-Augmented Generation (RAG) API designed for Azure Container Apps with a small CPU-only footprint and no heavy local LLM requirement.

## Goals

- Keep the project light enough for an 8 GB local machine
- Use an in-memory FAISS index instead of a heavy vector database
- Expose a retrieval tool compatible with MCP clients
- Return only the relevant document context, without final LLM synthesis in the API itself
- Deploy simply and cheaply on Azure Container Apps

## Architecture

- FastAPI app for HTTP access
- MCP-compatible tool for document retrieval
- FAISS + sentence chunking for local retrieval
- PDF ingestion from the project data folder
- Azure Container Apps for serverless deployment

## Project structure

```text
.
├── app/
│   ├── data/
│   ├── main.py
│   └── rag_engine.py
├── .github/
│   └── workflows/
│       └── deploy.yml
├── Dockerfile
├── .dockerignore
├── requirements.txt
├── README.md
├── scripts/
│   └── deploy-aca.sh
└── .env.example
```

## Local development

1. Create and activate a Python virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the API locally:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

4. Test the API:

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query":"Quelle est la durée maximale d\'un contrat de travail intérimaire pour le motif d\'insertion ?"}'
```

Expected response shape:

```json
{
  "query": "...",
  "context_extrait": "..."
}
```

## Docker

Build the image:

```bash
docker build -t rag-mcp-azure .
```

Run it locally:

```bash
docker run --rm -p 8000:8000 rag-mcp-azure
```

## Azure deployment

This project is designed for Azure Container Apps with a small CPU and memory profile.

### GitHub repository secrets

Add these secrets in GitHub:

- `AZURE_CREDENTIALS`
- `AZURE_CONTAINERAPPS_ENVIRONMENT`
- `ACR_USERNAME`
- `ACR_PASSWORD`

The Azure login step is already configured in [.github/workflows/deploy.yml](.github/workflows/deploy.yml):

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
