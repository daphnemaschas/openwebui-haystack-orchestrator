## OpenWebUI Haystack Orchestrator PoC

This PoC demonstrates an agentic orchestration layer that routes between tools
(data.gouv.fr search and Qdrant RAG) while keeping a simple Chainlit UI.
It mirrors the intent of OpenWebUI native tool mode: the LLM decides when to
respond directly or call tools in a loop, with visible tool steps.

The goal is to validate that a lightweight Hayhooks/Chainlit stack can:
- Load a Haystack pipeline with a custom Ollama generator.
- Run an agent loop that selects tools and iterates on results.
- Provide a friendly UI for testing data.gouv.fr dataset discovery.

### What is included

- Chainlit UI with an agent router and tool traces.
- Hayhooks service loading a generated Haystack pipeline.
- Tooling for data.gouv.fr datasets and Qdrant-backed RAG.

### Requirements

- Docker
- Ollama running locally (default: http://localhost:11434)
- Ollama models:
	- LLM: gemma4:e2b
	- Embeddings: nomic-embed-text

### Quick start

Copy the example environment file and edit if needed:

```bash
cp .env.example .env
```

Start the full stack:

```bash
make start
```

Open:

- Hayhooks: http://localhost:1416
- Chainlit: http://localhost:8000

### Test the PoC

1. Open Chainlit at http://localhost:8000.
2. Ask for the dataset:

```
Donne-moi le jeu de données "Repertoire national des elus" et liste le fichier
pour les conseillers d'arrondissements de Paris, Lyon et Marseille.
```

You should see tool steps for:
- `datagouv.search_data_gouv_datasets`
- `datagouv.list_dataset_files`
- optionally `datagouv.read_file_content`

### How it works

1. `make start` runs `pipelines/src/build_agent.py` to generate the YAML pipeline.
2. The pipeline definition is written to `pipelines/definitions/router_agent.yaml`.
3. Docker Compose starts Hayhooks and Chainlit.
4. Chainlit runs an agent loop that calls tools or answers directly.

### Configuration

- `.env.example` shows optional `OLLAMA_URL` and `OLLAMA_MODEL` values.
- `docker-compose.yml` sets defaults for Chainlit and Hayhooks.

### Troubleshooting

- If Chainlit returns a 500, check `docker compose logs --tail=200 hayhooks`.
- If tools cannot reach Ollama, verify http://localhost:11434 is reachable.
- If Qdrant is not available, the RAG tool will return a connectivity error.
