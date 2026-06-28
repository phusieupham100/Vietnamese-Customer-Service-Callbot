from copy import deepcopy

from vinfast_callbot.action_policy import (
    ACKNOWLEDGE_CORRECTION,
    ASK_INTENT_CLARIFICATION,
    ASK_MISSING_FIELD,
    CONFIRM_COLLECTED_INFORMATION,
    CONFIRM_VEHICLE_MODEL,
    HANDLE_EMERGENCY,
    TRANSFER_TO_HUMAN,
    ActionDecision,
)
from vinfast_callbot.models import Category, FieldState, FieldStatus, RoutingStatus, SessionState
from vinfast_callbot.response_generator import ResponseGenerator


def _state(
    category: Category | None = Category.G_1,
    fields: dict[str, object] | None = None,
    missing_fields: list[str] | None = None,
    confirmed_fields: list[str] | None = None,
) -> SessionState:
    fields = fields or {}
    confirmed_fields = confirmed_fields if confirmed_fields is not None else list(fields)
    return SessionState(
        session_id="call-001",
        category=category,
        routing_status=RoutingStatus.CONFIRMED if category else RoutingStatus.NEEDS_CLARIFICATION,
        fields=fields,
        missing_fields=missing_fields or [],
        confirmed_fields=confirmed_fields,
        field_states={
            name: FieldState(value=value, status=FieldStatus.CONFIRMED, confidence=0.95)
            for name, value in fields.items()
            if name in confirmed_fields
        },
    )


def test_intent_clarification_short_and_no_menu() -> None:
    response = ResponseGenerator().generate(
        ActionDecision(action=ASK_INTENT_CLARIFICATION, target_field="rescue_needed"),
        _state(category=None),
    )

    assert response.action == ASK_INTENT_CLARIFICATION
    assert response.response_text == "Dạ anh/chị có cần hỗ trợ cứu hộ ngay không ạ?"
    assert "G_1" not in response.response_text
    assert "bảo hành xe máy" not in response.response_text.lower()


def test_missing_phone_question() -> None:
    response = ResponseGenerator().generate(ASK_MISSING_FIELD, _state(), target_field="phone")

    assert response.response_text == "Dạ anh/chị cho em xin số điện thoại liên hệ ạ."
    assert "phone" not in response.response_text


def test_vehicle_model_confirmation() -> None:
    response = ResponseGenerator().generate(
        CONFIRM_VEHICLE_MODEL,
        _state(),
        target_field="vehicle_model",
        metadata={"candidates": ["VF 8"]},
    )

    assert response.response_text == "Dạ anh/chị đang sử dụng dòng xe VF 8 đúng không ạ?"
    assert "vehicle_model" not in response.response_text


def test_correction_acknowledgement_short() -> None:
    response = ResponseGenerator().generate(
        ACKNOWLEDGE_CORRECTION,
        _state(),
        metadata={"corrected_fields": ["phone"]},
    )

    assert response.response_text == "Dạ em đã cập nhật số điện thoại ạ."


def test_emergency_response_prioritizes_safety() -> None:
    response = ResponseGenerator().generate(HANDLE_EMERGENCY, _state(), metadata={"emergency_hotline": "1900-test"})

    assert "ưu tiên an toàn" in response.response_text
    assert "chuyển tư vấn viên" in response.response_text
    assert "1900-test" in response.response_text


def test_handoff_response_mentions_consultant_transfer() -> None:
    response = ResponseGenerator().generate(TRANSFER_TO_HUMAN, _state())

    assert "chuyển anh/chị đến tư vấn viên" in response.response_text


def test_final_confirmation_uses_only_existing_data() -> None:
    state = _state(
        fields={
            "full_name": "Nguyễn Văn Nam",
            "vehicle_model": "VF 8",
            "vehicle_condition": "hết pin",
        }
    )

    response = ResponseGenerator().generate(CONFIRM_COLLECTED_INFORMATION, state)

    assert "Nguyễn Văn Nam" in response.response_text
    assert "VF 8" in response.response_text
    assert "hết pin" in response.response_text
    assert "090" not in response.response_text


def test_does_not_ask_phone_and_vin_same_turn() -> None:
    state = _state(missing_fields=["phone", "license_plate_vin"])

    response = ResponseGenerator().generate(ASK_MISSING_FIELD, state, target_field="phone")

    assert "số điện thoại" in response.response_text
    assert "VIN" not in response.response_text
    assert "biển số" not in response.response_text


def test_confirmed_phone_is_not_asked_again() -> None:
    state = _state(
        fields={"phone": "0901234567"},
        missing_fields=["phone", "license_plate_vin"],
        confirmed_fields=["phone"],
    )

    response = ResponseGenerator().generate(ASK_MISSING_FIELD, state, target_field="phone")

    assert "số điện thoại" not in response.response_text
    assert "biển số" in response.response_text


def test_generator_does_not_mutate_state_or_action() -> None:
    state = _state(missing_fields=["phone"])
    before = deepcopy(state.to_dict())
    decision = ActionDecision(action=ASK_MISSING_FIELD, target_field="phone")

    response = ResponseGenerator().generate(decision, state)

    assert response.action == ASK_MISSING_FIELD
    assert decision.action == ASK_MISSING_FIELD
    assert state.to_dict() == before


def test_llm_failure_falls_back_to_deterministic_template() -> None:
    def failing_renderer(payload: dict[str, object]) -> str:
        raise RuntimeError("LLM unavailable")

    response = ResponseGenerator(llm_renderer=failing_renderer, use_llm=True).generate(
        ASK_MISSING_FIELD,
        _state(),
        target_field="phone",
    )

    assert response.used_fallback is True
    assert response.response_text == "Dạ anh/chị cho em xin số điện thoại liên hệ ạ."
