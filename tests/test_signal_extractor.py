from vinfast_callbot.signal_extractor import SignalExtractor


def test_signal_extractor_returns_required_internal_signals() -> None:
    signals = SignalExtractor().extract("Xe tôi hết pin")
    data = signals.to_dict()

    assert set(data) == {
        "service_goal",
        "vehicle_type",
        "vehicle_model",
        "vehicle_model_mention",
        "symptom",
        "can_move",
        "urgency",
        "explicit_rescue_request",
        "explicit_repair_request",
        "explicit_warranty_request",
        "explicit_order_request",
        "explicit_remote_support_request",
        "correction_detected",
    }
    assert data["service_goal"] == "unknown"
    assert data["symptom"] == "het pin"
    assert data["explicit_rescue_request"] is False


def test_extracts_explicit_rescue_request_without_routing() -> None:
    signals = SignalExtractor().extract("Xe tôi hết pin, tôi cần cứu hộ")

    assert signals.explicit_rescue_request is True
    assert signals.service_goal == "rescue"


def test_vehicle_model_mention_sets_confirmed_vehicle_type() -> None:
    extractor = SignalExtractor()

    car = extractor.extract("Xe VF8 bị lỗi, tôi muốn đặt lịch kiểm tra")
    motorbike = extractor.extract("Xe Feliz cần bảo hành")

    assert car.vehicle_model == "VF 8"
    assert car.vehicle_type == "car"
    assert motorbike.vehicle_model == "Feliz"
    assert motorbike.vehicle_type == "motorbike"


def test_remote_support_and_correction_signals() -> None:
    signals = SignalExtractor().extract("Không phải, hướng dẫn tôi khởi động lại màn hình")

    assert signals.explicit_remote_support_request is True
    assert signals.correction_detected is True
    assert signals.service_goal == "remote_support"
