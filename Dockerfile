FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt uv.lock /app/
COPY pipelines/src /app/pipelines/src

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

CMD ["python", "-c", "print('This image is optional; use docker compose up for OpenWebUI.')"]
