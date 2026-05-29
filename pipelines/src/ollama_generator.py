"""Haystack component for Ollama chat generation."""

import os
from typing import Optional

import ollama
from haystack import component


@component
class OllamaGenerator:
    """Haystack-compatible generator backed by Ollama chat."""

    def __init__(
        self,
        model: Optional[str] = None,
        host: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> None:
        """Initialize the Ollama generator.

        Args:
            model: Ollama model name.
            host: Ollama server URL.
            system_prompt: Optional system prompt for the chat.
        """
        self.model = model or os.getenv("OLLAMA_MODEL", "gemma4:e2b")
        self.host = host or os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.system_prompt = system_prompt
        self.client = ollama.Client(host=self.host)

    def run(self, prompt: str) -> dict:
        """Generate a reply for a prompt.

        Args:
            prompt: User prompt to send to the model.

        Returns:
            A dict containing a single-item "replies" list.
        """
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": prompt})
        response = self.client.chat(model=self.model, messages=messages)
        message = response.get("message", {})
        content = message.get("content") or ""
        return {"replies": [content]}
