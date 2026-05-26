FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock /app/
RUN uv sync --frozen --no-dev

ENV HAYHOOKS_HOST=0.0.0.0
ENV HAYHOOKS_PORT=1416
ENV HAYHOOKS_PIPELINES_DIR=/app/pipelines/definitions

EXPOSE 1416

CMD ["hayhooks", "run", "--host", "0.0.0.0", "--port", "1416"]
