"""ASR adapter interfaces used by the lightweight pipeline tests.

Người 1 owns real ASR implementation. This module only defines a small result
contract and a placeholder adapter so transcript-mode tests do not require
microphone, ASR, or TTS dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ASRResult:
    """Result returned by an ASR adapter."""

    transcript: str
    latency_ms: float = 0.0
    confidence: float | None = None
    error: str | None = None


class ASRAdapter:
    """Placeholder ASR adapter interface for Người 1 integration."""

    def transcribe(self, audio_path: str | None) -> ASRResult:
        """Transcribe audio and return an ASRResult.

        Real ASR is intentionally not implemented in Người 2. Inject a concrete
        adapter from the voice pipeline.
        """
        del audio_path
        return ASRResult(transcript="", error="ASR adapter is not configured")
