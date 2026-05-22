########################################################################################################################
# Project installation
########################################################################################################################

install:
	pip install -r requirements.txt

########################################################################################################################
# OpenWebUI
########################################################################################################################

start-ui:
	@echo "Lancement d'OpenWebUI sur http://localhost:3000..."
	docker compose up -d
	@echo "OpenWebUI est pret."

stop-ui:
	@echo "Arret d'OpenWebUI..."
	docker compose down

logs-ui:
	docker compose logs -f

start:
	./start.sh

restart-ui:
	@echo "Recreation du service OpenWebUI..."
	docker compose up -d --force-recreate openwebui

########################################################################################################################
# Qdrant RAG (CLI helpers)
########################################################################################################################

ingest-file:
	@if [ -z "$(FILE)" ]; then echo "Usage: make ingest-file FILE=data/rapport.txt [TITLE=...]"; exit 1; fi
	python - <<'PY'
from src.tools.qdrant_rag_tool import run
import os
file_path = os.environ.get("FILE")
title = os.environ.get("TITLE")
print(run(action="ingest", file_path=file_path, title=title))
PY

search-rag:
	@if [ -z "$(QUERY)" ]; then echo "Usage: make search-rag QUERY='...'"; exit 1; fi
	python - <<'PY'
from src.tools.qdrant_rag_tool import run
import os
query = os.environ.get("QUERY")
top_k = int(os.environ.get("TOP_K", "3"))
print(run(action="search", query=query, top_k=top_k))
PY
