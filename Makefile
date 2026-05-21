########################################################################################################################
# Project installation
########################################################################################################################

install:
	uv sync

########################################################################################################################
# Quality checks
########################################################################################################################

test:
	uv run pytest tests --cov src --cov-report term --cov-report=html --cov-report xml --junit-xml=tests-results.xml

format-check:
	uv run ruff format --check src tests

format-fix:
	uv run ruff format src tests

lint-check:
	uv run ruff check src tests

lint-fix:
	uv run ruff check src tests --fix

type-check:
	uv run mypy src

########################################################################################################################
# Api
########################################################################################################################

start-api:
	uv run uvicorn main:app --reload --port 8000

start-api-docker:
	docker compose up --build

stop-api-docker:
	docker compose down

########################################################################################################################
# Streamlit
########################################################################################################################

start-streamlit-app:
	uv run streamlit run "src/streamlit_app/🏠_Home_page.py"


########################################################################################################################
# OpenWebUI
########################################################################################################################

start-backend:
	@echo "Lancement de l'API orchestrateur sur le port 8000..."
	uv run uvicorn main:app --reload --port 8000

start-hayhooks:
	@echo "Lancement de Hayhooks + Chainlit UI sur le port 1416..."
	uv run hayhooks run --port 1416 --pipelines-dir ./pipelines --with-chainlit

start-ui:
	@echo "Vérification et lancement d'OpenWebUI sur http://localhost:3000..."
	@docker ps -a --format '{{.Names}}' | grep -q '^open-webui$$' && \
		(docker ps --format '{{.Names}}' | grep -q '^open-webui$$' || docker start open-webui) || \
		docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:main
	@echo "OpenWebUI est prêt !"

stop-ui:
	@echo "Arrêt du conteneur OpenWebUI..."
	docker stop open-webui

logs-ui:
	docker logs -f open-webui

dev: start-ui start-backend

index-docs:
	uv run python src/openwebui-haystack-orchestrator/index_documents.py