from vinfast_callbot.correction_detector import CorrectionDetector
from vinfast_callbot.models import (
    Category,
    VehicleMatchResult,
    VehicleMatchStatus,
    VehicleMatchType,
    VehicleType,
)


def test_detects_vehicle_model_correction_vf8_to_vf9() -> None:
    result = CorrectionDetector().detect(
        "Không phải VF8, xe của tôi là VF9",
        Category.G_1,
    )

    assert result.is_correction is True
    assert result.corrected_fields["vehicle_model"] == "VF 9"
    assert result.corrected_fields["vehicle_type"] == "car"


def test_detects_phone_correction() -> None:
    result = CorrectionDetector().detect(
        "Số điện thoại đúng là 0912345678",
        Category.G_1,
    )

    assert result.is_correction is True
    assert result.corrected_fields["phone"] == "0912345678"


def test_non_correction_turn_is_ignored() -> None:
    result = CorrectionDetector().detect("Xe VF8 bị hết pin", Category.G_1)

    assert result.is_correction is False
    assert result.corrected_fields == {}


def test_unknown_confirmed_vehicle_model_correction_is_preserved() -> None:
    match = VehicleMatchResult(
        raw_text="Zumo",
        canonical_name="Zumo",
        vehicle_type=VehicleType.UNKNOWN,
        match_type=VehicleMatchType.UNKNOWN,
        confidence=1.0,
        status=VehicleMatchStatus.UNKNOWN_CONFIRMED,
    )

    result = CorrectionDetector().detect(
        "Không phải Feliz, xe của tôi là Zumo",
        Category.G_4,
        vehicle_match_result=match,
    )

    assert result.is_correction is True
    assert result.corrected_fields["vehicle_line"] == "Zumo"
