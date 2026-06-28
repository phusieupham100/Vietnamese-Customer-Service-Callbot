from vinfast_callbot.dialogue import DialogueOrchestrator
from vinfast_callbot.models import DialogueAction, DialogueInput


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


def test_confirmed_category_output_has_schema_fields_and_no_candidates() -> None:
    engine = DialogueOrchestrator()

    engine.handle(_input("arch-1", 1, "Xe tôi bị chết máy giữa đường"))
    output = engine.handle(_input("arch-1", 2, "có"))

    data = output.to_dict()
    assert data["category"] == "G_1"
    assert data["candidate_categories"] == []
    assert data["fields"]["full_name"] is None
    assert data["fields"]["phone"] is None
    assert data["fields"]["vehicle_model"] is None
    assert data["pending_field"] == "full_name"
    assert output.next_action == DialogueAction.ASK_MISSING_FIELD


def test_dialogue_builds_final_call_output_with_schema_nulls() -> None:
    engine = DialogueOrchestrator()

    engine.handle(_input("arch-2", 1, "Tôi cần cứu hộ xe"))
    engine.handle(_input("arch-2", 2, "Lê Phương"))
    final_output = engine.build_final_call_output("arch-2", partial=True)

    assert final_output is not None
    data = final_output.to_dict()
    assert set(data) == {"category", "fields", "post_call"}
    assert data["category"] == "G_1"
    assert data["fields"]["full_name"] == "Lê Phương"
    assert data["fields"]["phone"] is None
    assert data["post_call"]["emergency"] == "no"
