"""Thin transcript/audio pipeline wrapper for integrating Dialogue Engine.

This module intentionally keeps business logic inside `dialogue.py` and the
Người 2 modules. It only adapts transcript or injected ASR output into the
DialogueInput contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from .asr import ASRAdapter
from .dialogue import DialogueOrchestrator
from .input_adapter import PipelineInput
from .models import DialogueInput


class DialogueManagerLike(Protocol):
    """Minimal interface required from a dialogue manager."""

    def handle_turn(self, dialogue_input: DialogueInput) -> dict[str, Any]:
        """Handle one dialogue turn and return a per-turn JSON-like dict."""


@dataclass(frozen=True, slots=True)
class PipelineResult:
    """Result returned by CallbotPipeline."""

    response_text: str
    transcript: str
    json: dict[str, Any]
    latency: dict[str, Any] = field(default_factory=dict)


class _DialogueOrchestratorAdapter:
    """Expose DialogueOrchestrator through the handle_turn protocol."""

    def __init__(self, orchestrator: DialogueOrchestrator | None = None) -> None:
        self.orchestrator = orchestrator if orchestrator is not None else DialogueOrchestrator()

    def handle_turn(self, dialogue_input: DialogueInput) -> dict[str, Any]:
        """Return DialogueOutput serialized as a dict."""
        return self.orchestrator.handle(dialogue_input).to_dict()


class CallbotPipeline:
    """Adapt runtime input into DialogueInput and call the dialogue manager."""

    def __init__(
        self,
        asr_adapter: ASRAdapter | None = None,
        dialogue_manager: DialogueManagerLike | None = None,
    ) -> None:
        self.asr_adapter = asr_adapter
        self.dialogue_manager = dialogue_manager if dialogue_manager is not None else _DialogueOrchestratorAdapter()
        self._turns_by_session: dict[str, int] = {}

    def handle_input(self, pipeline_input: PipelineInput) -> PipelineResult:
        """Handle transcript or injected-ASR input without microphone/TTS work."""
        transcript = pipeline_input.transcript.strip()
        latency: dict[str, Any] = {"input_mode": pipeline_input.input_mode}

        if pipeline_input.input_mode in {"audio_file", "microphone"}:
            if self.asr_adapter is None:
                return self._technical_error("", latency, "ASR adapter is not configured")
            asr_result = self.asr_adapter.transcribe(pipeline_input.audio_path)
            latency["asr_latency_ms"] = asr_result.latency_ms
            if asr_result.error:
                return self._technical_error(asr_result.transcript, latency, asr_result.error)
            transcript = asr_result.transcript

        turn_id = self._next_turn_id(pipeline_input.session_id)
        dialogue_json = self.dialogue_manager.handle_turn(
            DialogueInput(
                session_id=pipeline_input.session_id,
                turn_id=turn_id,
                transcript=transcript,
                input_mode=pipeline_input.input_mode,
                metadata=dict(pipeline_input.metadata),
            )
        )
        return PipelineResult(
            response_text=str(dialogue_json.get("response_text", "")),
            transcript=transcript,
            json=dict(dialogue_json),
            latency=latency,
        )

    def _next_turn_id(self, session_id: str) -> int:
        current = self._turns_by_session.get(session_id, 0) + 1
        self._turns_by_session[session_id] = current
        return current

    @staticmethod
    def _technical_error(transcript: str, latency: dict[str, Any], error: str) -> PipelineResult:
        return PipelineResult(
            response_text="Dạ hệ thống đang gặp lỗi kỹ thuật, em xin chuyển anh/chị đến tư vấn viên ạ.",
            transcript=transcript,
            json={
                "status": "error",
                "transfer_to_human": True,
                "handoff_reason": "system_error",
                "error": error,
            },
            latency=latency,
        )
