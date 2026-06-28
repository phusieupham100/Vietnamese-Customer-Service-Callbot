"""Basic tests for the Người 1 pipeline."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from vinfast_callbot.asr import ASRResult
from vinfast_callbot.input_adapter import InputAdapter
from vinfast_callbot.pipeline import CallbotPipeline


class FakeDialogueManager:
    def handle_turn(self, dialogue_input):
        transcript = dialogue_input.transcript
        if not transcript:
            return {
                "response_text": "Dạ em chưa nghe rõ thông tin, anh/chị vui lòng nói lại giúp em ạ.",
                "category": None,
                "fields": {},
                "missing_fields": [],
                "status": "collecting",
                "transfer_to_human": False,
                "emergency": False,
            }
        category = "G_1" if "cứu hộ" in transcript.lower() else None
        return {
            "response_text": "Dạ em đã ghi nhận yêu cầu từ model test.",
            "category": category,
            "fields": {"issue": "cứu hộ"} if category == "G_1" else {},
            "missing_fields": [],
            "status": "collecting",
            "transfer_to_human": False,
            "emergency": category == "G_1",
        }


class FakeASRAdapter:
    def __init__(self, transcript: str = "Tôi cần cứu hộ xe", error: str | None = None) -> None:
        self.transcript = transcript
        self.error = error

    def transcribe(self, audio_path: str | None) -> ASRResult:
        return ASRResult(
            transcript=self.transcript,
            latency_ms=1.0,
            confidence=0.99,
            error=self.error,
        )


class PipelineTests(unittest.TestCase):
    def test_transcript_turn_uses_dialogue_engine(self) -> None:
        adapter = InputAdapter()
        pipeline = CallbotPipeline(dialogue_manager=FakeDialogueManager())
        result = pipeline.handle_input(
            adapter.from_transcript("Tôi cần cứu hộ xe", session_id="test-session")
        )
        self.assertIn("model test", result.response_text.lower())
        self.assertEqual(result.json["category"], "G_1")
        self.assertEqual(result.transcript, "Tôi cần cứu hộ xe")

    def test_empty_transcript_returns_unclear_response(self) -> None:
        adapter = InputAdapter()
        pipeline = CallbotPipeline(dialogue_manager=FakeDialogueManager())
        result = pipeline.handle_input(adapter.from_transcript("   ", session_id="empty-session"))
        self.assertIn("chưa nghe rõ", result.response_text.lower())
        self.assertEqual(result.json["status"], "collecting")

    def test_audio_file_uses_asr_adapter(self) -> None:
        adapter = InputAdapter()
        pipeline = CallbotPipeline(
            asr_adapter=FakeASRAdapter(),
            dialogue_manager=FakeDialogueManager(),
        )
        with TemporaryDirectory() as tmpdir:
            audio = Path(tmpdir) / "demo.wav"
            audio.write_bytes(b"fake audio")
            result = pipeline.handle_input(
                adapter.from_audio_file(str(audio), session_id="audio-session")
            )
        self.assertEqual(result.transcript, "Tôi cần cứu hộ xe")
        self.assertEqual(result.json["category"], "G_1")

    def test_microphone_input_accepts_recorded_audio_path(self) -> None:
        adapter = InputAdapter()
        pipeline = CallbotPipeline(
            asr_adapter=FakeASRAdapter(),
            dialogue_manager=FakeDialogueManager(),
        )
        with TemporaryDirectory() as tmpdir:
            audio = Path(tmpdir) / "mic.wav"
            audio.write_bytes(b"fake audio")
            result = pipeline.handle_input(
                adapter.from_microphone(session_id="mic-session", audio_path=str(audio))
            )
        self.assertEqual(result.transcript, "Tôi cần cứu hộ xe")
        self.assertEqual(result.latency["input_mode"], "microphone")

    def test_audio_asr_error_returns_technical_error(self) -> None:
        adapter = InputAdapter()
        pipeline = CallbotPipeline(
            asr_adapter=FakeASRAdapter(transcript="", error="model missing"),
            dialogue_manager=FakeDialogueManager(),
        )
        result = pipeline.handle_input(
            adapter.from_audio_file("missing.wav", session_id="audio-error")
        )
        self.assertEqual(result.json["status"], "error")
        self.assertTrue(result.json["transfer_to_human"])


if __name__ == "__main__":
    unittest.main()
