import os
from typing import Optional

import ollama

import logging


logger = logging.getLogger(__name__)

class Pipe:
    def __init__(self) -> None:
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "gemma4:e2b")
        self.client = ollama.Client(host=self.ollama_url)

    def pipe(self, body: dict, __user__: Optional[dict] = None) -> str:
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