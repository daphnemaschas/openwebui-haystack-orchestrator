import json
import os
import uuid
import urllib.error
import urllib.parse
import urllib.request
from typing import Iterable, List, Optional

from .config import DEFAULT_COLLECTION, DEFAULT_EMBED_MODEL, get_env


def _post_json(url: str, payload: dict, timeout: int = 30) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _get_json(url: str, timeout: int = 20) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _ollama_embed(text: str, ollama_url: str, model: str) -> List[float]:
    url = f"{ollama_url.rstrip('/')}/api/embeddings"
    payload = {"model": model, "prompt": text}
    result = _post_json(url, payload)
    embedding = result.get("embedding")
    if not isinstance(embedding, list):
        raise ValueError("Missing embedding in Ollama response")
    return embedding


def _ensure_collection(qdrant_url: str, collection: str, vector_size: int) -> None:
    url = f"{qdrant_url.rstrip('/')}/collections/{urllib.parse.quote(collection)}"
    try:
        _get_json(url)
        return
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise

    payload = {
        "vectors": {
            "size": vector_size,
            "distance": "Cosine",
        }
    }
    _post_json(url, payload)


def _chunk_text(text: str, max_chars: int = 1200) -> Iterable[str]:
    if not text:
        return []

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    chunks: List[str] = []
    current: List[str] = []
    current_len = 0

    for line in lines:
        if current_len + len(line) + 1 > max_chars and current:
            chunks.append("\n".join(current))
            current = []
            current_len = 0
        current.append(line)
        current_len += len(line) + 1

    if current:
        chunks.append("\n".join(current))

    return chunks


def _fetch_source_text(source_url: str, max_chars: int = 200000) -> str:
    with urllib.request.urlopen(source_url, timeout=30) as response:
        content = response.read().decode("utf-8", errors="replace")
    return content[:max_chars]


def _read_local_file(file_path: str, max_chars: int = 200000) -> str:
    with open(file_path, "r", encoding="utf-8", errors="replace") as handle:
        return handle.read(max_chars)


def run(
    action: str = "search",
    query: Optional[str] = None,
    source_url: Optional[str] = None,
    file_path: Optional[str] = None,
    text: Optional[str] = None,
    title: Optional[str] = None,
    top_k: int = 3,
    collection: str = DEFAULT_COLLECTION,
) -> str:
    """Upload reports to Qdrant or search them using Ollama embeddings.

    Args:
        action: "ingest" to upload, "search" to query.
        query: Search query (required for action=search).
        source_url: URL to fetch text from (optional for ingest).
        file_path: Local path readable by the OpenWebUI container (optional for ingest).
        text: Raw text to ingest (optional for ingest).
        title: Optional title stored in metadata.
        top_k: Number of results for search.
        collection: Qdrant collection name.
    """
    qdrant_url = get_env("QDRANT_URL", "http://localhost:6333")
    ollama_url = get_env("OLLAMA_URL", "http://localhost:11434")
    embed_model = get_env("OLLAMA_EMBED_MODEL", DEFAULT_EMBED_MODEL)
    collection = get_env("QDRANT_COLLECTION", collection)

    if action not in {"ingest", "search"}:
        return "Invalid action. Use 'ingest' or 'search'."

    if action == "search":
        if not query:
            return "Missing query for search."
        embedding = _ollama_embed(query, ollama_url, embed_model)
        _ensure_collection(qdrant_url, collection, len(embedding))

        search_url = f"{qdrant_url.rstrip('/')}/collections/{urllib.parse.quote(collection)}/points/search"
        payload = {"vector": embedding, "limit": int(top_k)}
        result = _post_json(search_url, payload)
        hits = result.get("result", [])
        if not hits:
            return "No matches."
        lines = []
        for hit in hits:
            payload = hit.get("payload", {})
            snippet = payload.get("text") or ""
            if len(snippet) > 300:
                snippet = snippet[:300] + "..."
            lines.append(f"- {payload.get('title', 'document')} :: {snippet}")
        return "\n".join(lines)

    if not any([source_url, file_path, text]):
        return "Provide source_url, file_path, or text for ingest."

    try:
        if source_url:
            raw_text = _fetch_source_text(source_url)
        elif file_path:
            raw_text = _read_local_file(file_path)
        else:
            raw_text = text or ""
    except Exception as exc:
        return f"Failed to read source: {exc}"

    if not raw_text.strip():
        return "No text to ingest."

    chunks = list(_chunk_text(raw_text))
    if not chunks:
        return "No usable text chunks."

    embedding = _ollama_embed(chunks[0], ollama_url, embed_model)
    _ensure_collection(qdrant_url, collection, len(embedding))

    points = []
    for chunk in chunks:
        vector = _ollama_embed(chunk, ollama_url, embed_model)
        points.append(
            {
                "id": str(uuid.uuid4()),
                "vector": vector,
                "payload": {
                    "title": title or "datagouv_report",
                    "text": chunk,
                },
            }
        )

    upsert_url = f"{qdrant_url.rstrip('/')}/collections/{urllib.parse.quote(collection)}/points?wait=true"
    _post_json(upsert_url, {"points": points}, timeout=60)
    return f"Ingested {len(points)} chunks into {collection}."
