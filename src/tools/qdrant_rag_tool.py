"""Qdrant-backed RAG utilities with Ollama embeddings."""

import http.client
import json
import os
from pathlib import Path
import uuid
import urllib.error
import urllib.parse
import urllib.request
from typing import Iterable, List, Optional

DEFAULT_COLLECTION = "datagouv_reports"
DEFAULT_EMBED_MODEL = "nomic-embed-text"

def get_env(name: str, default: str) -> str:
    """Return an environment variable or a default fallback.

    Args:
        name: Environment variable name.
        default: Fallback value when unset or blank.

    Returns:
        The resolved environment value.
    """
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value


def _running_in_docker() -> bool:
    """Check whether the process is running in a Docker container.

    Returns:
        True if Docker or containerd markers are detected.
    """
    if os.path.exists("/.dockerenv"):
        return True
    try:
        with open("/proc/1/cgroup", "r", encoding="utf-8", errors="ignore") as handle:
            return any("docker" in line or "containerd" in line for line in handle)
    except OSError:
        return False


def _qdrant_candidates() -> List[str]:
    """Build a list of candidate Qdrant endpoints.

    Returns:
        Ordered list of URLs to probe.
    """
    env_url = os.getenv("QDRANT_URL", "").strip()
    if env_url:
        return [
            env_url,
            "http://localhost:6334",
            "http://127.0.0.1:6334",
            "http://host.docker.internal:6334",
            "http://host.docker.internal:6333",
            "http://qdrant:6333",
            "http://localhost:6333",
        ]

    if _running_in_docker():
        return [
            "http://qdrant:6333",
            "http://host.docker.internal:6333",
            "http://host.docker.internal:6334",
            "http://localhost:6334",
            "http://localhost:6333",
            "http://127.0.0.1:6334",
        ]

    return [
        "http://localhost:6334",
        "http://127.0.0.1:6334",
        "http://host.docker.internal:6334",
        "http://host.docker.internal:6333",
        "http://localhost:6333",
        "http://qdrant:6333",
    ]


def _resolve_qdrant_url() -> str:
    """Resolve a reachable Qdrant URL for local and container runs.

    Returns:
        The first reachable Qdrant URL, or a fallback.
    """
    env_url = os.getenv("QDRANT_URL", "").strip()
    candidates = _qdrant_candidates()

    seen = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            _get_json(f"{candidate.rstrip('/')}/collections", timeout=3)
            return candidate
        except Exception:
            continue

    return env_url or "http://localhost:6334"


def _ollama_candidates() -> List[str]:
    """Build a list of candidate Ollama endpoints.
    
    Returns:
        Ordered list of URLs to probe.
    """
    env_url = os.getenv("OLLAMA_URL", "").strip()
    if env_url:
        return [
            env_url,
            "http://localhost:11434",
            "http://127.0.0.1:11434",
            "http://host.docker.internal:11434",
        ]

    if _running_in_docker():
        return [
            "http://host.docker.internal:11434",
            "http://localhost:11434",
            "http://127.0.0.1:11434",
        ]

    return [
        "http://localhost:11434",
        "http://127.0.0.1:11434",
        "http://host.docker.internal:11434",
    ]


def _resolve_ollama_url() -> str:
    """Resolve a reachable Ollama URL for local and container runs.

    Returns:
        The first reachable Ollama URL, or a fallback.
    """
    env_url = os.getenv("OLLAMA_URL", "").strip()
    candidates = _ollama_candidates()

    seen = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            _get_json(f"{candidate.rstrip('/')}/api/version", timeout=3)
            return candidate
        except Exception:
            continue

    return env_url or "http://localhost:11434"


def _probe_url(url: str, path: str) -> str:
    """Probe a REST endpoint for availability.

    Args:
        url: Base URL to check.
        path: Path segment to request.

    Returns:
        "ok" on success or a descriptive error string.
    """
    try:
        _get_json(f"{url.rstrip('/')}/{path.lstrip('/')}", timeout=3)
        return "ok"
    except http.client.BadStatusLine:
        return "BadStatusLine: likely gRPC/TLS on this port (not REST)"
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"


def _post_json(url: str, payload: dict, timeout: int = 30) -> dict:
    """Send a POST request with a JSON payload.

    Args:
        url: Destination URL.
        payload: JSON-serializable payload.
        timeout: Request timeout in seconds.

    Returns:
        Parsed JSON response.
    """
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _put_json(url: str, payload: dict, timeout: int = 30) -> dict:
    """Send a PUT request with a JSON payload.

    Args:
        url: Destination URL.
        payload: JSON-serializable payload.
        timeout: Request timeout in seconds.

    Returns:
        Parsed JSON response.
    """
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="PUT",
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _get_json(url: str, timeout: int = 20) -> dict:
    """Fetch JSON from a URL.

    Args:
        url: Destination URL.
        timeout: Request timeout in seconds.

    Returns:
        Parsed JSON response.
    """
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _ollama_embed(text: str, ollama_url: str, model: str) -> List[float]:
    """Create an embedding for text using Ollama.

    Args:
        text: Input text to embed.
        ollama_url: Base URL of the Ollama server.
        model: Embedding model name.

    Returns:
        Embedding vector as a list of floats.

    Raises:
        RuntimeError: If the model is missing or incompatible.
        ValueError: If the response lacks an embedding.
    """
    url = f"{ollama_url.rstrip('/')}/api/embeddings"
    payload = {"model": model, "prompt": text}
    try:
        result = _post_json(url, payload)
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        if exc.code == 404:
            raise RuntimeError(
                f"Ollama model '{model}' not found. Pull an embedding model first, for example: ollama pull {model}"
            ) from exc
        if exc.code == 500 and "does not support embeddings" in body.lower():
            raise RuntimeError(
                f"Ollama model '{model}' does not support embeddings. Set OLLAMA_EMBED_MODEL to a dedicated embedding model such as 'nomic-embed-text'."
            ) from exc
        raise RuntimeError(f"Ollama embeddings request failed ({exc.code}): {body or exc.reason}") from exc
    embedding = result.get("embedding")
    if not isinstance(embedding, list):
        raise ValueError("Missing embedding in Ollama response")
    return embedding


def _ensure_collection(qdrant_url: str, collection: str, vector_size: int) -> None:
    """Create a Qdrant collection if it does not exist.

    Args:
        qdrant_url: Base URL of Qdrant.
        collection: Collection name.
        vector_size: Size of vectors stored in the collection.
    """
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
    _put_json(url, payload)


def _chunk_text(text: str, max_chars: int = 1200) -> Iterable[str]:
    """Split text into chunks suitable for embedding.

    Args:
        text: Raw text to chunk.
        max_chars: Maximum chunk size in characters.

    Returns:
        Iterable of chunk strings.
    """
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


def _keyword_score(query: str, text: str) -> int:
    """Compute a simple keyword overlap score.

    Args:
        query: Search query.
        text: Candidate text to score.

    Returns:
        Integer count of matched query terms.
    """
    terms = [t for t in query.lower().split() if len(t) > 2]
    if not terms:
        return 0
    haystack = text.lower()
    return sum(1 for t in terms if t in haystack)


def _fetch_source_text(source_url: str, max_chars: int = 200000) -> str:
    """Fetch and truncate text from a remote URL.

    Args:
        source_url: URL to fetch content from.
        max_chars: Maximum characters to return.

    Returns:
        Truncated text content.
    """
    with urllib.request.urlopen(source_url, timeout=30) as response:
        content = response.read().decode("utf-8", errors="replace")
    return content[:max_chars]


def _read_local_file(file_path: str, max_chars: int = 200000) -> str:
    """Read and truncate a local file or PDF.

    Args:
        file_path: Path to the local file.
        max_chars: Maximum characters to return.

    Returns:
        Extracted text content.

    Raises:
        RuntimeError: If PDF support is missing.
    """
    path = Path(file_path)
    if path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError(
                "PDF ingestion requires the 'pypdf' package. Run 'uv sync' to install dependencies."
            ) from exc

        reader = PdfReader(str(path))
        pages_text = []
        for page in reader.pages:
            extracted = page.extract_text() or ""
            if extracted.strip():
                pages_text.append(extracted)
        return "\n".join(pages_text)[:max_chars]

    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return handle.read(max_chars)


def run(
    action: str = "search",
    query: Optional[str] = None,
    source_url: Optional[str] = None,
    file_path: Optional[str] = None,
    text: Optional[str] = None,
    title: Optional[str] = None,
    top_k: int = 3,
    min_score: Optional[float] = None,
    collection: str = DEFAULT_COLLECTION,
) -> str:
    """Upload reports to Qdrant or search them using Ollama embeddings.

    Args:
        action: "ingest" to upload, "search" to query.
        query: Search query (required for action=search).
        source_url: URL to fetch text from (optional for ingest).
        file_path: Local path readable by the container (optional for ingest).
        text: Raw text to ingest (optional for ingest).
        title: Optional title stored in metadata.
        top_k: Number of results for search.
        min_score: Optional Qdrant score threshold.
        collection: Qdrant collection name.

    Returns:
        A human-readable result string.
    """
    qdrant_url = _resolve_qdrant_url()
    ollama_url = _resolve_ollama_url()
    embed_model = get_env("OLLAMA_EMBED_MODEL", DEFAULT_EMBED_MODEL)
    collection = get_env("QDRANT_COLLECTION", collection)

    if action not in {"ingest", "search"}:
        return "Invalid action. Use 'ingest' or 'search'."

    if action == "search":
        if not query:
            return "Missing query for search."
        try:
            embedding = _ollama_embed(query, ollama_url, embed_model)
        except Exception as exc:
            return f"Failed to create search embedding: {exc}"
        _ensure_collection(qdrant_url, collection, len(embedding))

        search_url = f"{qdrant_url.rstrip('/')}/collections/{urllib.parse.quote(collection)}/points/search"
        payload = {"vector": embedding, "limit": int(max(10, top_k)), "with_payload": True}
        if min_score is not None:
            payload["score_threshold"] = float(min_score)
        result = _post_json(search_url, payload)
        hits = result.get("result", [])
        if not hits:
            return "No matches."
        reranked = []
        for hit in hits:
            payload = hit.get("payload", {})
            text = payload.get("text") or ""
            score = _keyword_score(query, text)
            reranked.append((score, hit))

        reranked.sort(key=lambda item: item[0], reverse=True)
        lines = []
        for score, hit in reranked[:top_k]:
            payload = hit.get("payload", {})
            text = payload.get("text") or ""
            lines.append(f"- {payload.get('title', 'document')} :: {text}")
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

    try:
        embedding = _ollama_embed(chunks[0], ollama_url, embed_model)
    except Exception as exc:
        return f"Failed to create embeddings: {exc}"
    _ensure_collection(qdrant_url, collection, len(embedding))

    points = []
    for chunk in chunks:
        try:
            vector = _ollama_embed(chunk, ollama_url, embed_model)
        except Exception as exc:
            return f"Failed to create embeddings: {exc}"
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
    _put_json(upsert_url, {"points": points}, timeout=60)
    return f"Ingested {len(points)} chunks into {collection}."


class Tools:
    """Tool wrapper exposing Qdrant ingestion and search helpers."""

    def debug_endpoints(self) -> str:
        """Return connectivity diagnostics for Qdrant and Ollama endpoints.

        Returns:
            A formatted status report of candidate endpoints.
        """
        qdrant_lines = [
            f"{url} -> {_probe_url(url, 'collections')}" for url in _qdrant_candidates()
        ]
        ollama_lines = [
            f"{url} -> {_probe_url(url, 'api/version')}" for url in _ollama_candidates()
        ]
        return "Qdrant endpoints:\n" + "\n".join(qdrant_lines) + "\n\nOllama endpoints:\n" + "\n".join(ollama_lines)

    def ingest_report(
        self,
        source_url: Optional[str] = None,
        file_path: Optional[str] = None,
        text: Optional[str] = None,
        title: Optional[str] = None,
        collection: str = DEFAULT_COLLECTION,
    ) -> str:
        """Ingest a report into Qdrant for later retrieval.

        Args:
            source_url: Remote URL to ingest.
            file_path: Local file path to ingest.
            text: Raw text to ingest.
            title: Optional title stored in metadata.
            collection: Qdrant collection name.

        Returns:
            A summary of ingestion results.
        """
        return run(
            action="ingest",
            source_url=source_url,
            file_path=file_path,
            text=text,
            title=title,
            collection=collection,
        )

    def search_reports(
        self,
        query: str,
        top_k: int = 3,
        min_score: Optional[float] = None,
        collection: str = DEFAULT_COLLECTION,
    ) -> str:
        """Search the RAG corpus stored in Qdrant.

        CRITICAL: ALWAYS use this tool when the user asks a question about
        the CESEDA, immigration laws, ANEF, or residence cards.

        Args:
            query: Specific question to search for.
            top_k: Number of results to return (defaults to 3).
            min_score: Optional Qdrant score threshold.
            collection: Qdrant collection name.

        Returns:
            A formatted list of matching passages.
        """
        return run(
            action="search",
            query=query,
            top_k=top_k,
            min_score=min_score,
            collection=collection,
        )