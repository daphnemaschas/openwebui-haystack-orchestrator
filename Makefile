########################################################################################################################
# Project installation
########################################################################################################################

install:
	uv sync

########################################################################################################################
# Hayhooks + Chainlit
########################################################################################################################

build-pipeline:
	uv run python pipelines/src/build_agent.py

start: build-pipeline
	docker compose down
	docker compose up -d --build
	@echo "Hayhooks: http://localhost:1416"
	@echo "Chainlit: http://localhost:8000"

stop:
	docker compose down

logs:
	docker compose logs -f

restart:
	docker compose up -d --force-recreate
