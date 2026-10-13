"""
small client for the local Ollama HTTP API.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import settings


class OllamaError(RuntimeError):
    """represent a local Ollama connection or response failure."""


class OllamaClient:
    """call the local Ollama chat and generation endpoints."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
    ):
        # use explicit values in tests and configured defaults in the app
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model
        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.ollama_timeout_seconds
        )

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """send one JSON request to Ollama and return its JSON response."""

        request_body = None
        headers = {"Accept": "application/json"}

        if payload is not None:
            request_body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = Request(
            url=f"{self.base_url}{path}",
            data=request_body,
            headers=headers,
            method=method,
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise OllamaError(
                f"ollama returned HTTP {error.code}: {detail}"
            ) from error
        except URLError as error:
            raise OllamaError(
                "ollama is unavailable; start the local ollama service"
            ) from error
        except TimeoutError as error:
            raise OllamaError("ollama request timed out") from error

        try:
            return json.loads(response_body)
        except json.JSONDecodeError as error:
            raise OllamaError("ollama returned invalid JSON") from error

    def list_models(self) -> list[dict[str, Any]]:
        """return the models currently available in Ollama."""

        response = self._request("GET", "/api/tags")
        models = response.get("models", [])
        return models if isinstance(models, list) else []

    def chat(
        self,
        messages: Sequence[dict[str, Any]],
        tools: Sequence[dict[str, Any]] | None = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """send chat messages and optional manual tool definitions."""

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": list(messages),
            "stream": False,
            "options": {"temperature": temperature},
        }

        if tools:
            payload["tools"] = list(tools)

        return self._request("POST", "/api/chat", payload)

    def generate(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.2,
    ) -> str:
        """generate one plain-text response from Ollama."""

        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }

        if system:
            payload["system"] = system

        response = self._request("POST", "/api/generate", payload)
        generated_text = response.get("response")

        if not isinstance(generated_text, str):
            raise OllamaError("ollama response did not include generated text")

        return generated_text
