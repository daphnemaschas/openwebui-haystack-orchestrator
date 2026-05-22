FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml uv.lock README.md /app/
COPY pipelines/src /app/pipelines/src

RUN pip install --no-cache-dir --upgrade pip uv \
    && uv sync --frozen --no-dev

CMD ["python", "-c", "print('This image is optional; use docker compose up for OpenWebUI.')"]
