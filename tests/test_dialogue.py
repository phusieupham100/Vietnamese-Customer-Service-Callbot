from vinfast_callbot.models import DialogueAction, DialogueInput
from vinfast_callbot.dialogue import DialogueOrchestrator


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


def test_ambiguous_symptom_clarification_then_g1() -> None:
    engine = DialogueOrchestrator()

    first = engine.handle(_input("s1", 1, "Xe tôi hết pin"))
    second = engine.handle(_input("s1", 2, "Có, tôi cần cứu hộ"))

    assert first.category is None
    assert first.next_action == DialogueAction.ASK_INTENT_CLARIFICATION
    assert "cứu hộ" in first.response_text
    assert second.to_dict()["category"] == "G_1"
    assert second.next_action == DialogueAction.ASK_MISSING_FIELD
    assert second.to_dict()["candidate_categories"] == []
    assert second.to_dict()["fields"]["full_name"] is None
    assert second.to_dict()["fields"]["phone"] is None
    assert second.pending_field == "full_name"


def test_ambiguous_symptom_then_repair_routes_g2() -> None:
    engine = DialogueOrchestrator()

    engine.handle(_input("s2", 1, "Xe tôi không khởi động"))
    second = engine.handle(_input("s2", 2, "Không cần cứu hộ, tôi muốn hỏi lỗi này có được bảo hành không"))

    assert second.to_dict()["category"] == "G_2"
    assert "cứu hộ" not in second.response_text


def test_g3_happy_path() -> None:
    engine = DialogueOrchestrator()

    output = engine.handle(
        _input(
            "s3",
            1,
            "Tôi là Nguyễn Văn Nam, số 0901234567, mã đơn ABC123, khách hàng cá nhân, bao giờ đơn xe được giao?",
        )
    )

    data = output.to_dict()
    assert data["category"] == "G_3"
    assert data["fields"]["full_name"] == "Nguyễn Văn Nam"
    assert data["fields"]["order_phone"] == "0901234567"
    assert data["fields"]["order_code_dealer"] == "ABC123"
    assert data["fields"]["customer_type"] == "personal"
    assert output.next_action == DialogueAction.CONFIRM_COLLECTED_INFORMATION


def test_g4_vehicle_model_recognition() -> None:
    output = DialogueOrchestrator().handle(
        _input("s4", 1, "Xe Feliz cần bảo hành, tôi là An, số 0901234567, biển số 29B-12345, ở Cầu Giấy, xe bị lỗi pin")
    )

    data = output.to_dict()
    assert data["category"] == "G_4"
    assert data["fields"]["vehicle_line"] == "Feliz"


def test_g5_troubleshooting_flow() -> None:
    output = DialogueOrchestrator().handle(
        _input(
            "s5",
            1,
            "Hướng dẫn tôi khởi động lại màn hình, tôi là Nam, số 0901234567, xe VF8, VIN LJSKA123456789012, xe bị treo màn hình",
        )
    )

    assert output.to_dict()["category"] == "G_5"
    assert output.next_action == DialogueAction.PROVIDE_REMOTE_STEP
    assert "khởi động lại" in output.response_text


def test_correction_updates_state_and_acknowledges() -> None:
    engine = DialogueOrchestrator()

    engine.handle(_input("s6", 1, "Xe VF8 bị lỗi, tôi muốn đặt lịch kiểm tra"))
    output = engine.handle(_input("s6", 2, "Không phải VF8, xe của tôi là VF9"))

    state = engine.get_state("s6")
    assert state is not None
    assert state.fields["vehicle_model"] == "VF 9"
    assert "full_name" not in state.fields
    assert output.next_action == DialogueAction.ACKNOWLEDGE_CORRECTION
    assert "cập nhật" in output.response_text


def test_unclear_phone_confirms_field() -> None:
    output = DialogueOrchestrator().handle(
        _input("s7", 1, "Xe tôi hết pin, tôi cần cứu hộ, số điện thoại không rõ")
    )

    assert output.next_action == DialogueAction.CONFIRM_UNCLEAR_FIELD
    assert output.pending_field == "phone"
    assert "số điện thoại" in output.response_text


def test_emergency() -> None:
    output = DialogueOrchestrator().handle(_input("s8", 1, "Xe tai nạn, có người bị thương"))

    assert output.next_action == DialogueAction.HANDLE_EMERGENCY
    assert output.emergency is True
    assert output.transfer_to_human is True


def test_two_failed_turns() -> None:
    engine = DialogueOrchestrator()

    first = engine.handle(_input("s9", 1, "", asr_confidence=0.1))
    second = engine.handle(_input("s9", 2, "", asr_confidence=0.1))

    assert first.next_action == DialogueAction.REPEAT_OR_REPHRASE
    assert second.next_action == DialogueAction.TRANSFER_TO_HUMAN
    assert second.transfer_to_human is True


def test_hangup_partial() -> None:
    output = DialogueOrchestrator().handle(
        _input("s10", 1, "", event_type="hangup")
    )

    assert output.next_action == DialogueAction.END_PARTIAL_CALL
    assert output.status.value == "partial"
    assert output.should_end_call is True


def test_unknown_model_confirmation() -> None:
    output = DialogueOrchestrator().handle(_input("s11", 1, "Xe Zumo cần bảo hành"))

    assert output.next_action == DialogueAction.ASK_INTENT_CLARIFICATION
    assert output.to_dict()["category"] is None


def test_multi_field_input() -> None:
    output = DialogueOrchestrator().handle(
        _input(
            "s12",
            1,
            "Xe tôi hết pin, tôi cần cứu hộ. Tôi là Nguyễn Văn Nam, số 0901234567, xe VF8 ở đường Láng Hà Nội, biển số 30A-12345, odo 25000 km",
        )
    )

    data = output.to_dict()
    assert data["category"] == "G_1"
    assert data["fields"]["full_name"] == "Nguyễn Văn Nam"
    assert data["fields"]["phone"] == "0901234567"
    assert data["fields"]["vehicle_model"] == "VF 8"
    assert data["fields"]["license_plate_vin"] == "30A-12345"
    assert data["fields"]["current_odo"] == 25000


def test_partial_transcript_does_not_update_state() -> None:
    engine = DialogueOrchestrator()

    output = engine.handle(_input("s13", 1, "Xe tôi hết pin", is_final_transcript=False))

    assert output.response_text == ""
    assert engine.get_state("s13") is None


def test_out_of_scope_handoff() -> None:
    output = DialogueOrchestrator().handle(_input("s14", 1, "Toi muon mua dien thoai"))

    assert output.next_action == DialogueAction.TRANSFER_TO_HUMAN
    assert output.transfer_to_human is True
    assert output.handoff_reason.value == "out_of_scope"


def test_pending_full_name_does_not_reask_after_name_answer() -> None:
    engine = DialogueOrchestrator()

    engine.handle(_input("s15", 1, "xe tôi bị chết máy giữa đường"))
    engine.handle(_input("s15", 2, "có"))
    engine.handle(_input("s15", 3, "tôi ở Lương Thế Vinh, Từ Liêm"))
    engine.handle(_input("s15", 4, "hà nội"))
    engine.handle(_input("s15", 5, "0375889750"))
    output = engine.handle(_input("s15", 6, "Lê Thị Phương"))

    data = output.to_dict()
    assert data["fields"]["full_name"] == "Lê Thị Phương"
    assert data["pending_field"] != "full_name"
    assert "họ tên" not in output.response_text.lower()
