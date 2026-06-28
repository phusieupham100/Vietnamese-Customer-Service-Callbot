from vinfast_callbot.emergency_detector import EmergencyDetector


def test_vehicle_cannot_start_is_not_emergency() -> None:
    detector = EmergencyDetector()

    result = detector.detect("Xe không khởi động")

    assert result.is_emergency is False


def test_accident_with_injury_is_emergency() -> None:
    detector = EmergencyDetector()

    result = detector.detect("Xe tai nạn, có người bị thương")

    assert result.is_emergency is True
    assert result.reason == "accident_with_injury"


def test_fire_is_emergency() -> None:
    assert EmergencyDetector.is_emergency("Xe đang cháy và bốc khói") is True


def test_symptom_only_false_positive_cases() -> None:
    detector = EmergencyDetector()

    assert detector.detect("Xe tôi hết pin").is_emergency is False
    assert detector.detect("Xe báo lỗi trên màn hình").is_emergency is False
