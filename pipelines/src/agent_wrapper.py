"""OpenWebUI-compatible pipe wrapper for Ollama chat."""

import os
from typing import Optional

import ollama

import logging


logger = logging.getLogger(__name__)


class Pipe:
    """Pipe wrapper that forwards chat messages to Ollama."""

    def __init__(self) -> None:
        """Initialize the Ollama client and defaults."""
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "gemma4:e2b")
        self.client = ollama.Client(host=self.ollama_url)

    def pipe(self, body: dict, __user__: Optional[dict] = None) -> str:
        """Process an OpenWebUI-style request body.

        Args:
            body: Request payload containing a "messages" list.
            __user__: Optional user metadata (unused).

        Returns:
            Model response text or an error message.
        """
        messages = body.get("messages", [])
        if not messages:
            return "Missing messages in request."

        try:
            response = self.client.chat(model=self.ollama_model, messages=messages)
        except Exception as exc:
            logger.exception("Ollama chat failed")
            return f"Ollama error: {exc}"

        message = response.get("message", {})
        content = message.get("content")
        return content or ""