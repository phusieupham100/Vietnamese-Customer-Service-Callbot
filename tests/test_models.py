"""Tests for Dialogue Engine data models."""

from __future__ import annotations

import pytest

from vinfast_callbot.models import (
    CallStatus,
    Category,
    DialogueAction,
    DialogueInput,
    DialogueOutput,
    ExtractionResult,
    FieldState,
    FieldStatus,
    FinalCallOutput,
    PostCallOutput,
    RoutingResult,
    RoutingStatus,
    SessionState,
    VehicleMatchResult,
)


def test_dialogue_input_serializes_contract_shape() -> None:
    model = DialogueInput(
        session_id="call-001",
        turn_id=3,
        transcript="Xe tôi bị chết máy trên cao tốc",
        input_mode="microphone",
        history=[{"role": "user", "content": "Xe tôi đang có vấn đề"}],
        metadata={"asr_confidence": 0.87},
    )

    data = model.to_dict()

    assert data["session_id"] == "call-001"
    assert data["turn_id"] == 3
    assert data["metadata"]["asr_confidence"] == 0.87


def test_dialogue_output_accepts_valid_enums() -> None:
    output = DialogueOutput(
        response_text="Dạ anh/chị có cần hỗ trợ cứu hộ ngay không ạ?",
        category=None,
        routing_status="needs_clarification",
        candidate_categories=["G_1", "G_2", "G_5"],
        pending_field="rescue_needed",
        next_action="ASK_INTENT_CLARIFICATION",
        status="routing",
    )

    data = output.to_dict()

    assert data["routing_status"] == "needs_clarification"
    assert data["candidate_categories"] == ["G_1", "G_2", "G_5"]
    assert data["next_action"] == "ASK_INTENT_CLARIFICATION"
    assert data["status"] == "routing"


def test_invalid_dialogue_action_is_rejected() -> None:
    with pytest.raises(ValueError, match="Invalid next_action"):
        DialogueOutput(response_text="bad", next_action="BAD_ACTION")


def test_invalid_category_is_rejected() -> None:
    with pytest.raises(ValueError, match="Invalid category"):
        DialogueOutput(response_text="bad", category="G_9")


def test_session_state_serializes_field_states() -> None:
    state = SessionState(
        session_id="call-001",
        category=Category.G_1,
        routing_status=RoutingStatus.CONFIRMED,
        field_states={"phone": FieldState(value="0901234567", status=FieldStatus.CONFIRMED)},
        last_action=DialogueAction.ASK_MISSING_FIELD,
        status=CallStatus.COLLECTING,
    )

    data = state.to_dict()

    assert data["category"] == "G_1"
    assert data["field_states"]["phone"]["status"] == "confirmed"
    assert data["last_action"] == "ASK_MISSING_FIELD"


def test_routing_and_extraction_models() -> None:
    routing = RoutingResult(
        category=None,
        routing_status="needs_clarification",
        confidence=0.61,
        candidate_categories=["G_1", "G_2", "G_5"],
        missing_discriminator="rescue_needed",
    )
    extraction = ExtractionResult(
        fields={"vehicle_condition": "xe không khởi động được"},
        internal_signals={"explicit_rescue_request": False},
    )

    assert routing.to_dict()["candidate_categories"] == ["G_1", "G_2", "G_5"]
    assert extraction.to_dict()["fields"]["vehicle_condition"] == "xe không khởi động được"


def test_vehicle_match_result_model() -> None:
    match = VehicleMatchResult(
        raw_text="ép tám",
        canonical_name="VF 8",
        vehicle_type="car",
        match_type="alias",
        confidence=0.98,
        status="confirmed",
    )

    assert match.to_dict()["vehicle_type"] == "car"
    assert match.to_dict()["match_type"] == "alias"


def test_final_call_output_serializes_only_contract_keys() -> None:
    output = FinalCallOutput(
        category="G_1",
        fields={"full_name": "Nguyễn Văn Nam"},
        post_call=PostCallOutput(
            short_summary="Khách cần hỗ trợ.",
            sentimental_analysis="urgent",
            emergency="yes",
        ),
    )

    data = output.to_dict()

    assert set(data) == {"category", "fields", "post_call"}
    assert data["category"] == "G_1"
    assert data["post_call"]["emergency"] == "yes"

