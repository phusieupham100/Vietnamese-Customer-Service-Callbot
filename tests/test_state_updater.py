from vinfast_callbot.correction_detector import CorrectionDetectionResult
from vinfast_callbot.models import Category, ExtractionResult, FieldState, FieldStatus, SessionState
from vinfast_callbot.state_updater import StateUpdater


def _state_with_fields(
    category: Category,
    fields: dict[str, object],
    statuses: dict[str, FieldStatus] | None = None,
) -> SessionState:
    statuses = statuses or {name: FieldStatus.CONFIRMED for name in fields}
    return SessionState(
        session_id="call-001",
        turn_id=1,
        category=category,
        fields=dict(fields),
        field_states={
            name: FieldState(
                value=value,
                status=statuses.get(name, FieldStatus.CONFIRMED),
                source_turn=1,
                confidence=0.95 if statuses.get(name, FieldStatus.CONFIRMED) == FieldStatus.CONFIRMED else 0.5,
            )
            for name, value in fields.items()
        },
        confirmed_fields=[
            name
            for name in fields
            if statuses.get(name, FieldStatus.CONFIRMED) == FieldStatus.CONFIRMED
        ],
        conversation_history=[{"role": "user", "content": "old"}],
    )


def test_vehicle_model_correction_vf8_to_vf9_updates_model_and_type() -> None:
    old_state = _state_with_fields(Category.G_1, {"vehicle_model": "VF 8", "vehicle_type": "car"})
    correction = CorrectionDetectionResult(
        is_correction=True,
        corrected_fields={"vehicle_model": "VF 9", "vehicle_type": "car"},
        field_confidences={"vehicle_model": 0.99, "vehicle_type": 0.99},
    )

    new_state = StateUpdater().update(old_state, correction_result=correction)

    assert new_state.fields["vehicle_model"] == "VF 9"
    assert new_state.fields["vehicle_type"] == "car"
    assert new_state.field_states["vehicle_model"].to_dict()["corrected"] is True
    assert new_state.field_states["vehicle_model"].to_dict()["status"] == "corrected"


def test_phone_correction_replaces_old_phone() -> None:
    old_state = _state_with_fields(Category.G_1, {"phone": "0900000000"})
    correction = CorrectionDetectionResult(
        is_correction=True,
        corrected_fields={"phone": "0912345678"},
        field_confidences={"phone": 0.99},
    )

    new_state = StateUpdater().update(old_state, correction_result=correction)

    assert new_state.fields["phone"] == "0912345678"
    assert new_state.unconfirmed_fields == {}
    assert new_state.field_states["phone"].to_dict()["corrected"] is True


def test_confirmed_phone_is_not_lost_when_new_turn_omits_it() -> None:
    old_state = _state_with_fields(Category.G_1, {"phone": "0900000000"})

    new_state = StateUpdater().update(
        old_state,
        extraction_result=ExtractionResult(fields={"vehicle_condition": "het pin"}),
    )

    assert new_state.fields["phone"] == "0900000000"
    assert new_state.fields["vehicle_condition"] == "het pin"
    assert "phone" in new_state.confirmed_fields


def test_low_confidence_new_value_does_not_overwrite_confirmed_field() -> None:
    old_state = _state_with_fields(Category.G_1, {"phone": "0900000000"})

    new_state = StateUpdater().update(
        old_state,
        extraction_result=ExtractionResult(fields={"phone": "0912345678"}),
        field_confidences={"phone": 0.4},
    )

    assert new_state.fields["phone"] == "0900000000"


def test_unconfirmed_field_can_be_replaced_by_more_confident_value() -> None:
    old_state = _state_with_fields(
        Category.G_1,
        {"phone": "090000000"},
        statuses={"phone": FieldStatus.UNCONFIRMED},
    )

    new_state = StateUpdater().update(
        old_state,
        extraction_result=ExtractionResult(fields={"phone": "0901234567"}),
        field_confidences={"phone": 0.95},
    )

    assert new_state.fields["phone"] == "0901234567"
    assert "phone" in new_state.confirmed_fields


def test_missing_fields_are_computed_for_category() -> None:
    old_state = _state_with_fields(Category.G_3, {"full_name": "Nguyễn Văn Nam"})

    new_state = StateUpdater().update(old_state)

    assert new_state.missing_fields == ["order_phone", "order_code_dealer", "customer_type"]
    assert new_state.pending_field == "order_phone"


def test_category_change_from_g1_to_g2_keeps_common_valid_fields_and_history() -> None:
    old_state = _state_with_fields(
        Category.G_1,
        {
            "full_name": "Nguyễn Văn Nam",
            "phone": "0900000000",
            "vehicle_model": "VF 8",
            "vehicle_type": "car",
            "current_location": "đường Láng",
            "vehicle_condition": "het pin",
        },
    )

    new_state = StateUpdater().update(old_state, category=Category.G_2)

    assert new_state.fields == {
        "full_name": "Nguyễn Văn Nam",
        "vehicle_model": "VF 8",
        "vehicle_condition": "het pin",
    }
    assert new_state.conversation_history == [{"role": "user", "content": "old"}]
    assert "phone" not in new_state.fields
    assert "vehicle_type" not in new_state.fields


def test_unknown_confirmed_vehicle_model_is_kept() -> None:
    old_state = SessionState(session_id="call-001", category=Category.G_4)

    new_state = StateUpdater().update(
        old_state,
        extraction_result=ExtractionResult(fields={"vehicle_line": "Zumo"}),
        field_confidences={"vehicle_line": 1.0},
    )

    assert new_state.fields["vehicle_line"] == "Zumo"
    assert new_state.field_states["vehicle_line"].to_dict()["status"] == "confirmed"


def test_uncertain_field_goes_to_unconfirmed_and_pending() -> None:
    old_state = SessionState(session_id="call-001", category=Category.G_1)

    new_state = StateUpdater().update(
        old_state,
        extraction_result=ExtractionResult(uncertain_fields={"phone": "không rõ"}),
    )

    assert new_state.unconfirmed_fields["phone"] == "không rõ"
    assert new_state.pending_field == "phone"
    assert new_state.field_states["phone"].to_dict()["status"] == "unconfirmed"


def test_no_reask_metadata_for_confirmed_fields() -> None:
    state = _state_with_fields(Category.G_1, {"phone": "0900000000", "full_name": "Nguyễn Văn Nam"})
    updater = StateUpdater()

    metadata = updater.no_reask_metadata(state)

    assert updater.should_ask_field(state, "phone") is False
    assert metadata.to_dict() == {"fields": ["full_name", "phone"]}
