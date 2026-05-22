## OpenWebUI + Ollama (pipe local)

This repo keeps a single OpenWebUI pipe that forwards chat messages to Ollama.
There is no separate API server or Haystack pipeline.

### Requirements

- Ollama running locally (default: http://localhost:11434)
- Docker (for OpenWebUI)

### Quick start

```bash
docker compose up -d
```

Then open http://localhost:3000 and use the OpenWebUI pipe.

### Configuration

The pipe reads these environment variables (from the OpenWebUI container):

- `OLLAMA_URL` (default: http://localhost:11434)
- `OLLAMA_MODEL` (default: gemma4:e2b)

You can change them in [docker-compose.yml](docker-compose.yml).
