"""OpenAI API client used by the production Dialogue Engine path.

The client calls the OpenAI Responses API directly with the standard library.
It intentionally has no SDK dependency and does not contain mock behavior.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol


class LLMClientError(RuntimeError):
    """Raised when a local LLM call fails or returns an invalid response."""


class LLMClient(Protocol):
    """Protocol implemented by production and test LLM clients."""

    def chat(self, messages: list[dict[str, str]]) -> str:
        """Return assistant text for chat messages."""


@dataclass(frozen=True, slots=True)
class OpenAIAPIConfig:
    """Configuration for OpenAI Responses API."""

    responses_url: str
    model: str
    api_key: str | None = None
    timeout_seconds: float = 30.0

    @classmethod
    def from_env(cls) -> "OpenAIAPIConfig":
        """Build config from environment variables."""
        return cls(
            responses_url=os.getenv("VINFAST_OPENAI_RESPONSES_URL", "https://api.openai.com/v1/responses"),
            model=os.getenv("VINFAST_OPENAI_MODEL", os.getenv("OPENAI_MODEL", "gpt-4.1")),
            api_key=os.getenv("OPENAI_API_KEY") or os.getenv("VINFAST_OPENAI_API_KEY") or None,
            timeout_seconds=float(os.getenv("VINFAST_OPENAI_TIMEOUT_SECONDS", "30")),
        )


class OpenAIAPIClient:
    """Call OpenAI Responses API and return assistant text."""

    def __init__(self, config: OpenAIAPIConfig | None = None) -> None:
        self.config = config if config is not None else OpenAIAPIConfig.from_env()

    def chat(self, messages: list[dict[str, str]]) -> str:
        """Send messages to OpenAI and return assistant content."""
        if not self.config.api_key:
            raise LLMClientError("OPENAI_API_KEY is not configured")

        payload = {
            "model": self.config.model,
            "input": self._responses_input(messages),
            "temperature": 0.0,
            "text": {"format": {"type": "json_object"}},
        }
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }

        request = urllib.request.Request(
            self.config.responses_url,
            data=body,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise LLMClientError(f"OpenAI API call failed: {exc}") from exc

        try:
            data = json.loads(raw)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise LLMClientError("OpenAI API response is not valid JSON") from exc

        content = self._extract_output_text(data)

        if not isinstance(content, str) or not content.strip():
            raise LLMClientError("OpenAI API returned empty content")
        return content

    @staticmethod
    def _responses_input(messages: list[dict[str, str]]) -> list[dict[str, object]]:
        return [
            {
                "role": message["role"],
                "content": [{"type": "input_text", "text": message["content"]}],
            }
            for message in messages
        ]

    @staticmethod
    def _extract_output_text(data: dict[str, Any]) -> str:
        output_text = data.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text

        for item in data.get("output", []):
            if not isinstance(item, dict):
                continue
            for part in item.get("content", []):
                if isinstance(part, dict) and part.get("type") == "output_text":
                    text = part.get("text")
                    if isinstance(text, str) and text.strip():
                        return text
        raise LLMClientError("OpenAI API response does not contain output_text")


# Backward-compatible alias for older imports/tests.
LocalLLMConfig = OpenAIAPIConfig
LocalLLMClient = OpenAIAPIClient
