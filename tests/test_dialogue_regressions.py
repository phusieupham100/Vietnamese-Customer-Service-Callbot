from vinfast_callbot.dialogue import DialogueOrchestrator
from vinfast_callbot.models import DialogueInput


def _input(session_id: str, turn_id: int, transcript: str, **metadata: object) -> DialogueInput:
    base_metadata = {"is_final_transcript": True, "event_type": "user_utterance"}
    base_metadata.update(metadata)
    return DialogueInput(
        session_id=session_id,
        turn_id=turn_id,
        transcript=transcript,
        input_mode="transcript",
        metadata=base_metadata,
    )


def test_pending_license_plate_accepts_direct_answer_and_moves_on() -> None:
    engine = DialogueOrchestrator()

    engine.handle(_input("regression-plate", 1, "xe toi bi chet may giua duong"))
    engine.handle(_input("regression-plate", 2, "co"))
    engine.handle(_input("regression-plate", 3, "toi ten la Phuong"))
    engine.handle(_input("regression-plate", 4, "0375889750"))
    engine.handle(_input("regression-plate", 5, "V8"))
    output = engine.handle(_input("regression-plate", 6, "30A18397"))

    data = output.to_dict()
    assert data["fields"]["vehicle_model"] == "VF 8"
    assert data["fields"]["license_plate_vin"] == "30A-18397"
    assert data["pending_field"] != "license_plate_vin"
    assert "bien so" not in output.response_text.lower()
