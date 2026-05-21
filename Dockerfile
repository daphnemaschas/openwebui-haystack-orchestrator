FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml uv.lock README.md /app/
COPY src /app/src
COPY main.py /app/main.py

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
