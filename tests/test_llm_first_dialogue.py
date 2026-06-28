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


def test_semantically_equivalent_emergencies_route_to_g1() -> None:
    examples = [
        "Tôi vừa đâm vào cột điện.",
        "Xe vừa lao vào một vật bên đường.",
        "Người ngồi sau đang choáng sau cú va chạm.",
        "Có người trong xe không ra ngoài được.",
    ]

    for index, transcript in enumerate(examples, start=1):
        engine = DialogueOrchestrator()
        output = engine.handle(_input(f"emergency-{index}", 1, transcript))

        assert output.to_dict()["category"] == "G_1"
        assert output.emergency is True
        assert output.next_action == DialogueAction.HANDLE_EMERGENCY
        assert output.pending_field == "current_location"
        assert "vị trí" in output.response_text.lower()
        assert engine.last_turn_log["turn_analyzer_backend"] == "llm"
        assert engine.last_turn_log["llm_called"] is True
        assert engine.last_turn_log["llm_parse_success"] is True
        assert engine.last_turn_log["rule_fallback_used"] is False


def test_non_emergency_vehicle_faults_do_not_trigger_emergency() -> None:
    examples = ["Xe không khởi động.", "Xe hết pin.", "Màn hình bị treo."]

    for index, transcript in enumerate(examples, start=1):
        output = DialogueOrchestrator().handle(_input(f"non-emergency-{index}", 1, transcript))

        assert output.emergency is False
        assert output.next_action != DialogueAction.HANDLE_EMERGENCY


def test_pending_full_name_short_answer_is_understood_by_llm_analyzer() -> None:
    engine = DialogueOrchestrator()

    engine.handle(_input("pending-name", 1, "Xe tôi chết máy giữa đường"))
    engine.handle(_input("pending-name", 2, "có"))
    output = engine.handle(_input("pending-name", 3, "Lê Thị Phương"))

    assert output.to_dict()["fields"]["full_name"] == "Lê Thị Phương"


def test_history_allows_later_turn_to_become_emergency() -> None:
    engine = DialogueOrchestrator()

    first = engine.handle(_input("history-emergency", 1, "Xe tôi đang có vấn đề."))
    second = engine.handle(_input("history-emergency", 2, "Người ngồi sau đang choáng sau cú va chạm."))

    assert first.emergency is False
    assert second.to_dict()["category"] == "G_1"
    assert second.emergency is True
    assert second.next_action == DialogueAction.HANDLE_EMERGENCY
