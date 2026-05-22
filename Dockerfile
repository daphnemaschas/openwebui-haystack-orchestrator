FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml uv.lock /app/
COPY openwebui/pipes /app/openwebui/pipes

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir ollama

CMD ["python", "-c", "print('This image is optional; use docker compose up for OpenWebUI.')"]
