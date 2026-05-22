import urllib.error
import urllib.parse
import urllib.request

from .config import DEFAULT_MCP_REF, DEFAULT_MCP_REPO_RAW_BASE


def run(path: str = "README.md", ref: str = DEFAULT_MCP_REF, max_chars: int = 4000) -> str:
    """Fetch a file from the datagouv-mcp repo on GitHub.

    Args:
        path: Path in the repo (ex: README.md, docs/..., etc.).
        ref: Git ref or branch (default: main).
        max_chars: Truncate response to this many characters.
    """
    safe_path = path.lstrip("/")
    url = f"{DEFAULT_MCP_REPO_RAW_BASE}/{urllib.parse.quote(ref)}/{urllib.parse.quote(safe_path)}"

    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            content = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return f"GitHub request failed: HTTP {exc.code}"
    except Exception as exc:
        return f"GitHub request failed: {exc}"

    if max_chars and len(content) > max_chars:
        content = content[:max_chars] + "\n... (truncated)"

    return content
