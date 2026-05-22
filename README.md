## PoC Haystack OpenWebUI

This repo provides a minimal OpenWebUI setup with a local Ollama-backed pipe.
The pipe lives in [pipelines/src/agent_wrapper.py](pipelines/src/agent_wrapper.py) and is mounted into OpenWebUI.

### Requirements

- Ollama running locally (default: http://localhost:11434)
- Docker (for OpenWebUI)

### Quick start

```bash
./start.sh
```

Then open http://localhost:3000 and use the OpenWebUI pipe.

### Configuration

The pipe reads these environment variables (from the OpenWebUI container):

- `OLLAMA_URL` (default: http://localhost:11434)
- `OLLAMA_MODEL` (default: gemma4:e2b)

You can change them in [docker-compose.yml](docker-compose.yml).
