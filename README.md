## Mymirai agentic orchestrator (Haystack + Ollama)

This repo hosts a small agentic orchestrator that runs inside this codebase, without relying on the OpenWebUI backend
for LLM responses. It uses Haystack + Ollama, and exposes a `/chat` API.

### Requirements

- Python 3.11+
- Ollama running locally (default: http://localhost:11434)
- Qdrant (optional but recommended for RAG)

### Quick start (local)

```bash
uv sync
uv run python src/openwebui-haystack-orchestrator/index_documents.py
uv run uvicorn main:app --reload --port 8000
```

Then call the API:

```bash
curl -sS http://localhost:8000/chat \
	-H 'Content-Type: application/json' \
	-d '{"messages":[{"role":"user","content":"Quels sont les conditions de renouvellement ?"}]}'
```

### Docker compose

```bash
docker compose up --build
```

### Configuration (.env)

Copy `.env.example` to `.env` and adjust as needed:

- `OLLAMA_URL` (default: http://localhost:11434)
- `OLLAMA_MODEL` (default: gemma4:e2b)
- `QDRANT_HOST` (default: localhost)
- `QDRANT_PORT` (default: 6333)
- `QDRANT_INDEX` (default: ceseda_collection)
- `EMBEDDING_DIM` (default: 384)
- `DATA_DIR` (default: data)

### Tools included

- `rag_search`: semantic search in Qdrant index
- `keyword_search`: keyword search in local `data/` files
- `calculator`: basic arithmetic evaluation
