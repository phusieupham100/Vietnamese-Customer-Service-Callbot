"""Input adapters for transcript, audio-file, and microphone handoff modes."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class PipelineInput:
    """Normalized input passed into the lightweight pipeline wrapper."""

    session_id: str
    input_mode: str
    transcript: str = ""
    audio_path: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


class InputAdapter:
    """Build PipelineInput objects without touching microphone or ASR directly."""

    def from_transcript(self, transcript: str, session_id: str = "default") -> PipelineInput:
        """Create transcript-mode input."""
        return PipelineInput(
            session_id=session_id,
            input_mode="transcript",
            transcript=transcript,
            metadata={"is_final_transcript": True, "event_type": "user_utterance"},
        )

    def from_audio_file(self, audio_path: str, session_id: str = "default") -> PipelineInput:
        """Create audio-file input for an injected ASR adapter."""
        return PipelineInput(
            session_id=session_id,
            input_mode="audio_file",
            audio_path=audio_path,
            metadata={"is_final_transcript": True, "event_type": "user_utterance"},
        )

    def from_microphone(self, session_id: str = "default", audio_path: str | None = None) -> PipelineInput:
        """Create microphone-mode input from an already recorded audio path."""
        return PipelineInput(
            session_id=session_id,
            input_mode="microphone",
            audio_path=audio_path,
            metadata={"is_final_transcript": True, "event_type": "user_utterance"},
        )
