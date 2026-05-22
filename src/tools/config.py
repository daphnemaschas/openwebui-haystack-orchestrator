import os

DEFAULT_COLLECTION = "datagouv_reports"
DEFAULT_EMBED_MODEL = "nomic-embed-text"
DEFAULT_MCP_REF = "main"
DEFAULT_MCP_REPO_RAW_BASE = "https://raw.githubusercontent.com/datagouv/datagouv-mcp"


def get_env(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value
