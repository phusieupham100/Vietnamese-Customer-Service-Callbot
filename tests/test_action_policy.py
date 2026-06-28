from vinfast_callbot.action_policy import (
    ACKNOWLEDGE_CORRECTION,
    ASK_INTENT_CLARIFICATION,
    ASK_MISSING_FIELD,
    ASK_REMOTE_STEP_RESULT,
    CONFIRM_COLLECTED_INFORMATION,
    CONFIRM_UNCLEAR_FIELD,
    CONFIRM_VEHICLE_MODEL,
    END_PARTIAL_CALL,
    FINALIZE_CALL,
    HANDLE_EMERGENCY,
    PROVIDE_REMOTE_STEP,
    TRANSFER_TO_HUMAN,
    DialogueActionPolicy,
)
from vinfast_callbot.correction_detector import CorrectionDetectionResult
from vinfast_callbot.models import Category, FieldState, FieldStatus, RoutingStatus, SessionState


def _state(
    category: Category | None = Category.G_1,
    fields: dict[str, object] | None = None,
    missing_fields: list[str] | None = None,
    unconfirmed_fields: dict[str, object] | None = None,
    confirmed_fields: list[str] | None = None,
    pending_field: str | None = None,
    failed_turn_count: int = 0,
    emergency: bool = False,
) -> SessionState:
    fields = fields or {}
    confirmed_fields = confirmed_fields if confirmed_fields is not None else list(fields)
    field_states = {
        name: FieldState(value=value, status=FieldStatus.CONFIRMED, confidence=0.95)
        for name, value in fields.items()
        if name in confirmed_fields
    }
    for name, value in (unconfirmed_fields or {}).items():
        field_states[name] = FieldState(value=value, status=FieldStatus.UNCONFIRMED, confidence=0.5)
    return SessionState(
        session_id="call-001",
        category=category,
        routing_status=RoutingStatus.CONFIRMED if category is not None else RoutingStatus.NEEDS_CLARIFICATION,
        fields=fields,
        field_states=field_states,
        confirmed_fields=confirmed_fields,
        missing_fields=missing_fields or [],
        unconfirmed_fields=unconfirmed_fields or {},
        pending_field=pending_field,
        failed_turn_count=failed_turn_count,
        emergency=emergency,
    )


def test_emergency_has_highest_priority() -> None:
    state = _state(
        missing_fields=["phone"],
        unconfirmed_fields={"phone": "không rõ"},
        pending_field="phone",
        failed_turn_count=2,
        emergency=True,
    )

    decision = DialogueActionPolicy().decide(state)

    assert decision.action == HANDLE_EMERGENCY


def test_unclear_intent_asks_intent_clarification() -> None:
    state = _state(category=None, pending_field="rescue_needed")

    decision = DialogueActionPolicy().decide(state)

    assert decision.action == ASK_INTENT_CLARIFICATION
    assert decision.target_field == "rescue_needed"


def test_unclear_phone_confirms_phone() -> None:
    state = _state(
        unconfirmed_fields={"phone": "không rõ"},
        pending_field="phone",
    )

    decision = DialogueActionPolicy().decide(state)

    assert decision.action == CONFIRM_UNCLEAR_FIELD
    assert decision.target_field == "phone"


def test_unclear_vehicle_model_uses_vehicle_confirmation_action() -> None:
    state = _state(
        unconfirmed_fields={"vehicle_model": "green bus tám"},
        pending_field="vehicle_model",
    )

    decision = DialogueActionPolicy().decide(state)

    assert decision.action == CONFIRM_VEHICLE_MODEL
    assert decision.target_field == "vehicle_model"


def test_missing_phone_asks_only_phone() -> None:
    state = _state(missing_fields=["phone", "license_plate_vin"], pending_field="phone")

    decision = DialogueActionPolicy().decide(state)

    assert decision.action == ASK_MISSING_FIELD
    assert decision.target_field == "phone"
    assert isinstance(decision.target_field, str)


def test_confirmed_phone_is_not_asked_again() -> None:
    state = _state(
        fields={"phone": "0901234567"},
        missing_fields=["license_plate_vin"],
        pending_field="license_plate_vin",
    )

    decision = DialogueActionPolicy().decide(state)

    assert decision.action == ASK_MISSING_FIELD
    assert decision.target_field == "license_plate_vin"


def test_category_not_confirmed_does_not_ask_required_fields() -> None:
    state = SessionState(
        session_id="call-001",
        category=None,
        routing_status=RoutingStatus.NEEDS_CLARIFICATION,
        missing_fields=["phone"],
        pending_field="phone",
    )

    decision = DialogueActionPolicy().decide(state)

    assert decision.action == ASK_INTENT_CLARIFICATION
    assert decision.action != ASK_MISSING_FIELD


def test_correction_acknowledged_before_handoff() -> None:
    state = _state(failed_turn_count=2)
    correction = CorrectionDetectionResult(
        is_correction=True,
        corrected_fields={"phone": "0912345678"},
    )

    decision = DialogueActionPolicy().decide(state, correction_result=correction)

    assert decision.action == ACKNOWLEDGE_CORRECTION
    assert decision.metadata["corrected_fields"] == ["phone"]


def test_enough_required_fields_goes_to_confirmation_then_finalize() -> None:
    fields = {
        "full_name": "Nguyễn Văn Nam",
        "phone": "0901234567",
        "vehicle_model": "VF 8",
        "license_plate_vin": "30A-12345",
        "vehicle_type": "car",
        "current_odo": 12000,
        "current_location": "đường Láng",
        "city_name": "Hà Nội",
        "vehicle_condition": "het pin",
    }

    confirmation = DialogueActionPolicy().decide(_state(fields=fields))
    finalized = DialogueActionPolicy().decide(_state(fields={**fields, "_final_confirmation_done": True}))

    assert confirmation.action == CONFIRM_COLLECTED_INFORMATION
    assert finalized.action == FINALIZE_CALL


def test_two_failed_turns_transfer_to_human() -> None:
    state = _state(failed_turn_count=2)

    decision = DialogueActionPolicy().decide(state)

    assert decision.action == TRANSFER_TO_HUMAN


def test_hangup_returns_partial_action() -> None:
    state = _state(missing_fields=["phone"], pending_field="phone")

    decision = DialogueActionPolicy().decide(state, event_type="hangup")

    assert decision.action == END_PARTIAL_CALL


def test_g5_unresolved_provides_next_remote_step() -> None:
    state = _state(
        category=Category.G_5,
        fields={
            "full_name": "Nguyễn Văn Nam",
            "phone": "0901234567",
            "license_plate_vin": "30A-12345",
            "vehicle_line": "VF 8",
            "vehicle_condition_details": "màn hình treo",
            "troubleshooting": {"steps_attempted": [], "resolved": False},
        },
    )

    decision = DialogueActionPolicy().decide(state)

    assert decision.action == PROVIDE_REMOTE_STEP


def test_g5_awaiting_result_asks_remote_step_result() -> None:
    state = _state(
        category=Category.G_5,
        fields={
            "full_name": "Nguyễn Văn Nam",
            "phone": "0901234567",
            "license_plate_vin": "30A-12345",
            "vehicle_line": "VF 8",
            "vehicle_condition_details": "màn hình treo",
            "troubleshooting": {"steps_attempted": ["restart_screen"], "awaiting_result": True, "resolved": False},
        },
    )

    decision = DialogueActionPolicy().decide(state)

    assert decision.action == ASK_REMOTE_STEP_RESULT


def test_g5_unresolved_after_max_steps_transfers() -> None:
    state = _state(
        category=Category.G_5,
        fields={
            "full_name": "Nguyễn Văn Nam",
            "phone": "0901234567",
            "license_plate_vin": "30A-12345",
            "vehicle_line": "VF 8",
            "vehicle_condition_details": "màn hình treo",
            "troubleshooting": {
                "steps_attempted": ["restart_screen", "check_connection"],
                "max_steps": 2,
                "resolved": False,
            },
        },
    )

    decision = DialogueActionPolicy().decide(state)

    assert decision.action == TRANSFER_TO_HUMAN
