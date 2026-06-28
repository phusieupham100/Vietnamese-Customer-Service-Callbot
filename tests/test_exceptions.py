from vinfast_callbot.action_policy import (
    ACKNOWLEDGE_CORRECTION,
    ASK_INTENT_CLARIFICATION,
    ASK_MISSING_FIELD,
    CONFIRM_UNCLEAR_FIELD,
    CONFIRM_VEHICLE_MODEL,
    END_PARTIAL_CALL,
    HANDLE_EMERGENCY,
    REPEAT_OR_REPHRASE,
    TRANSFER_TO_HUMAN,
)
from vinfast_callbot.correction_detector import CorrectionDetectionResult
from vinfast_callbot.exceptions import ExceptionHandler, ExceptionHandlerConfig, ExceptionReasonCode
from vinfast_callbot.models import (
    Category,
    RoutingStatus,
    SessionState,
    VehicleMatchResult,
    VehicleMatchStatus,
    VehicleMatchType,
    VehicleType,
)


def test_missing_field_exception() -> None:
    state = SessionState(
        session_id="call-001",
        category=Category.G_1,
        routing_status=RoutingStatus.CONFIRMED,
        missing_fields=["phone", "license_plate_vin"],
        pending_field="phone",
    )

    result = ExceptionHandler().handle("Xe tôi hết pin", state)

    assert result.reason_code == ExceptionReasonCode.MISSING_FIELD.value
    assert result.action == ASK_MISSING_FIELD
    assert result.target_field == "phone"


def test_customer_corrects_information_exception() -> None:
    state = SessionState(session_id="call-001", category=Category.G_1, routing_status=RoutingStatus.CONFIRMED)
    correction = CorrectionDetectionResult(
        is_correction=True,
        corrected_fields={"vehicle_model": "VF 9"},
        evidence=["khong phai"],
    )

    result = ExceptionHandler().handle("Không phải VF8, xe tôi là VF9", state, correction_result=correction)

    assert result.reason_code == ExceptionReasonCode.CUSTOMER_CORRECTION.value
    assert result.action == ACKNOWLEDGE_CORRECTION
    assert result.metadata["corrected_fields"] == ["vehicle_model"]


def test_ambiguous_intent_exception() -> None:
    state = SessionState(
        session_id="call-001",
        category=None,
        routing_status=RoutingStatus.NEEDS_CLARIFICATION,
        pending_field="rescue_needed",
    )

    result = ExceptionHandler().handle("Xe tôi hết pin", state)

    assert result.reason_code == ExceptionReasonCode.AMBIGUOUS_INTENT.value
    assert result.action == ASK_INTENT_CLARIFICATION
    assert result.target_field == "rescue_needed"


def test_out_of_scope_exception_handoff() -> None:
    state = SessionState(session_id="call-001", category=None)

    result = ExceptionHandler().handle("Tôi muốn mua điện thoại", state)

    assert result.reason_code == ExceptionReasonCode.OUT_OF_SCOPE.value
    assert result.action == TRANSFER_TO_HUMAN
    assert result.should_handoff is True
    assert result.handoff_reason == "out_of_scope"


def test_unclear_empty_transcript_exception() -> None:
    state = SessionState(session_id="call-001", category=Category.G_1)

    result = ExceptionHandler().handle("", state)

    assert result.reason_code == ExceptionReasonCode.UNCLEAR_TRANSCRIPT.value
    assert result.action == REPEAT_OR_REPHRASE
    assert result.state_updates == {"failed_turn_count_delta": 1}


def test_garbled_phone_or_vin_exception() -> None:
    state = SessionState(
        session_id="call-001",
        category=Category.G_1,
        unconfirmed_fields={"license_plate_vin": "không rõ"},
        pending_field="license_plate_vin",
    )

    result = ExceptionHandler().handle("Biển số không rõ", state)

    assert result.reason_code == ExceptionReasonCode.UNCLEAR_FIELD.value
    assert result.action == CONFIRM_UNCLEAR_FIELD
    assert result.target_field == "license_plate_vin"


def test_emergency_positive_uses_configured_hotline() -> None:
    state = SessionState(session_id="call-001", category=Category.G_1)
    handler = ExceptionHandler(config=ExceptionHandlerConfig(emergency_hotline="1900-test"))

    result = handler.handle("Xe tai nạn, có người bị thương", state)

    assert result.reason_code == ExceptionReasonCode.EMERGENCY_DETECTED.value
    assert result.action == HANDLE_EMERGENCY
    assert result.should_handoff is True
    assert result.handoff_reason == "emergency"
    assert result.metadata["emergency_hotline"] == "1900-test"


def test_emergency_negative_for_normal_vehicle_error() -> None:
    state = SessionState(session_id="call-001", category=Category.G_1)

    result = ExceptionHandler().handle("Xe không khởi động", state)

    assert result.reason_code != ExceptionReasonCode.EMERGENCY_DETECTED.value
    assert result.action != HANDLE_EMERGENCY


def test_failed_turn_count_exception() -> None:
    state = SessionState(session_id="call-001", category=Category.G_1, failed_turn_count=2)

    result = ExceptionHandler().handle("Tôi vẫn chưa rõ", state)

    assert result.reason_code == ExceptionReasonCode.FAILED_UNDERSTANDING_LIMIT.value
    assert result.action == TRANSFER_TO_HUMAN
    assert result.handoff_reason == "failed_understanding"


def test_customer_hangup_partial_call() -> None:
    state = SessionState(session_id="call-001", category=Category.G_1, missing_fields=["phone"])

    result = ExceptionHandler().handle("", state, event_type="hangup")

    assert result.reason_code == ExceptionReasonCode.CUSTOMER_HANGUP.value
    assert result.action == END_PARTIAL_CALL
    assert result.partial is True
    assert result.state_updates["status"] == "partial"
    assert result.state_updates["should_end_call"] is True


def test_customer_request_handoff() -> None:
    state = SessionState(session_id="call-001", category=Category.G_1)

    result = ExceptionHandler().handle("Cho tôi gặp tư vấn viên", state)

    assert result.reason_code == ExceptionReasonCode.CUSTOMER_REQUESTS_AGENT.value
    assert result.action == TRANSFER_TO_HUMAN
    assert result.handoff_reason == "customer_request"


def test_ambiguous_vehicle_model_exception_does_not_map_candidate() -> None:
    state = SessionState(session_id="call-001", category=Category.G_1)
    match = VehicleMatchResult(
        raw_text="green bus tám",
        canonical_name=None,
        vehicle_type=VehicleType.CAR,
        match_type=VehicleMatchType.AMBIGUOUS,
        confidence=0.66,
        status=VehicleMatchStatus.NEEDS_CONFIRMATION,
        candidates=["Green Bus 6M", "Green Bus 8M", "Green Bus 10M"],
    )

    result = ExceptionHandler().handle("Xe Green Bus tám", state, vehicle_match_result=match)

    assert result.reason_code == ExceptionReasonCode.AMBIGUOUS_VEHICLE_MODEL.value
    assert result.action == CONFIRM_VEHICLE_MODEL
    assert result.target_field == "vehicle_model"
    assert result.metadata["raw_text"] == "green bus tám"
    assert "canonical_name" not in result.metadata


def test_unknown_vehicle_model_exception_does_not_map_nearby_model() -> None:
    state = SessionState(session_id="call-001", category=Category.G_4)
    match = VehicleMatchResult(
        raw_text="Zumo",
        canonical_name=None,
        vehicle_type=VehicleType.UNKNOWN,
        match_type=VehicleMatchType.UNKNOWN,
        confidence=0.0,
        status=VehicleMatchStatus.UNKNOWN,
    )

    result = ExceptionHandler().handle("Xe Zumo", state, vehicle_match_result=match)

    assert result.reason_code == ExceptionReasonCode.UNKNOWN_VEHICLE_MODEL.value
    assert result.action == CONFIRM_VEHICLE_MODEL
    assert result.metadata["raw_text"] == "Zumo"
    assert result.metadata["candidates"] == []


def test_remote_fix_failed_optional_exception() -> None:
    state = SessionState(
        session_id="call-001",
        category=Category.G_5,
        fields={"troubleshooting": {"failed": True}},
    )

    result = ExceptionHandler().handle("Vẫn không được", state)

    assert result.reason_code == ExceptionReasonCode.REMOTE_FIX_FAILED.value
    assert result.action == TRANSFER_TO_HUMAN
    assert result.handoff_reason == "remote_fix_failed"
