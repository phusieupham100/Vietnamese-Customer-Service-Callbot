from vinfast_callbot.extractor import CategoryFieldExtractor
from vinfast_callbot.models import (
    Category,
    VehicleMatchResult,
    VehicleMatchStatus,
    VehicleMatchType,
    VehicleType,
)


def test_extracts_multiple_fields_in_one_sentence_for_g1() -> None:
    result = CategoryFieldExtractor().extract(
        Category.G_1,
        "Tôi là Nguyễn Văn Nam, số 0901234567, xe VF8 bị chết máy ở đường Láng, Hà Nội, biển số 30A-12345, odo 25000 km.",
    )

    assert result.fields["full_name"] == "Nguyễn Văn Nam"
    assert result.fields["phone"] == "0901234567"
    assert result.fields["vehicle_model"] == "VF 8"
    assert result.fields["vehicle_type"] == "car"
    assert result.fields["license_plate_vin"] == "30A-12345"
    assert result.fields["current_odo"] == 25000
    assert result.fields["current_location"] == "đường Láng"
    assert result.fields["city_name"] == "Hà Nội"
    assert "chết máy" in result.fields["vehicle_condition"]


def test_does_not_hallucinate_missing_fields() -> None:
    result = CategoryFieldExtractor().extract(Category.G_1, "Xe tôi hết pin")

    assert result.fields == {"vehicle_condition": "het pin"}


def test_g3_does_not_extract_license_plate_vin() -> None:
    result = CategoryFieldExtractor().extract(
        Category.G_3,
        "Tôi là Nguyễn Văn Nam, số 0901234567, mã đơn VFORD123, biển số 30A-12345, khách hàng cá nhân.",
    )

    assert "license_plate_vin" not in result.fields
    assert "license_plate_vin" not in result.uncertain_fields
    assert result.fields["order_phone"] == "0901234567"
    assert result.fields["order_code_dealer"] == "VFORD123"
    assert result.fields["customer_type"] == "personal"


def test_pending_full_name_accepts_short_name_answer() -> None:
    result = CategoryFieldExtractor().extract(
        Category.G_1,
        "Lê Thị Phương",
        existing_fields={"pending_field": "full_name"},
    )

    assert result.fields["full_name"] == "Lê Thị Phương"


def test_unicode_full_name_phrase_is_extracted() -> None:
    result = CategoryFieldExtractor().extract(Category.G_1, "tôi tên là Lê Phương")

    assert result.fields["full_name"] == "Lê Phương"


def test_g2_uses_owner_phone_not_phone() -> None:
    result = CategoryFieldExtractor().extract(
        Category.G_2,
        "Tôi là Nguyễn Văn Nam, số 0901234567, xe VF8 dùng cá nhân, muốn kiểm tra ở trung tâm Mỹ Đình.",
    )

    assert "phone" not in result.fields
    assert result.fields["owner_phone"] == "0901234567"


def test_g3_uses_order_phone() -> None:
    result = CategoryFieldExtractor().extract(Category.G_3, "Số đơn hàng 0901234567, mã đơn ABC123.")

    assert "phone" not in result.fields
    assert result.fields["order_phone"] == "0901234567"


def test_g4_uses_vehicle_line() -> None:
    result = CategoryFieldExtractor().extract(Category.G_4, "Xe Feliz cần bảo hành, số 0901234567.")

    assert result.fields["vehicle_line"] == "Feliz"
    assert "vehicle_model" not in result.fields


def test_unknown_vehicle_model_is_not_mapped_to_nearby_catalog_model() -> None:
    unknown = VehicleMatchResult(
        raw_text="Zumo",
        canonical_name=None,
        vehicle_type=VehicleType.UNKNOWN,
        match_type=VehicleMatchType.UNKNOWN,
        confidence=0.0,
        status=VehicleMatchStatus.UNKNOWN,
    )

    result = CategoryFieldExtractor().extract(Category.G_4, "Xe Zumo cần bảo hành", vehicle_match_result=unknown)

    assert "vehicle_line" not in result.fields
    assert result.uncertain_fields["vehicle_line"] == "Zumo"


def test_unclear_phone_or_vin_goes_to_uncertain_fields() -> None:
    result = CategoryFieldExtractor().extract(Category.G_1, "Số điện thoại không rõ, biển số không rõ.")

    assert result.fields == {}
    assert result.uncertain_fields["phone"] == "không rõ"
    assert result.uncertain_fields["license_plate_vin"] == "không rõ"


def test_odo_normalizes_to_int_when_clear() -> None:
    result = CategoryFieldExtractor().extract(Category.G_1, "ODO 12.345 km.")

    assert result.fields["current_odo"] == 12345


def test_field_outside_schema_is_dropped_by_category_schema() -> None:
    result = CategoryFieldExtractor().extract(Category.G_3, "Xe VF8 biển số 30A-12345, mã đơn ABC123.")

    assert result.fields == {"order_code_dealer": "ABC123"}
    assert "vehicle_model" not in result.fields
    assert "license_plate_vin" not in result.fields
