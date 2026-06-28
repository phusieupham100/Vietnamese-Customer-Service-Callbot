from vinfast_callbot.models import Category
from vinfast_callbot.validators import FieldValidator, JSONValidator


def test_json_validator_accepts_basic_turn_output() -> None:
    validator = JSONValidator()
    output = {
        "response_text": "ok",
        "category": "G_1",
        "fields": {},
        "missing_fields": [],
        "status": "collecting",
        "transfer_to_human": False,
        "emergency": False,
    }

    result = validator.validate_turn_output(output)

    assert result.ok is True
    assert result.errors == []


def test_json_validator_rejects_invalid_category() -> None:
    result = JSONValidator().validate_turn_output(
        {
            "response_text": "ok",
            "category": "BAD",
            "fields": {},
            "missing_fields": [],
            "status": "collecting",
            "transfer_to_human": False,
            "emergency": False,
        }
    )

    assert result.ok is False
    assert "Invalid category" in result.errors[0]


def test_json_validator_parse_json_object() -> None:
    parsed, errors = JSONValidator().parse_json_object('{"response_text": "ok"}')

    assert errors == []
    assert parsed == {"response_text": "ok"}


def test_phone_fields_normalize_by_category_specific_name() -> None:
    validator = FieldValidator()

    owner = validator.validate_field(Category.G_2, "owner_phone", "+84 901 234 567")
    order = validator.validate_field(Category.G_3, "order_phone", "0901234567")

    assert owner.ok is True
    assert owner.value == "0901234567"
    assert order.ok is True
    assert order.value == "0901234567"


def test_unclear_phone_and_vin_are_uncertain() -> None:
    validator = FieldValidator()

    phone = validator.validate_field(Category.G_1, "phone", "không rõ")
    vin = validator.validate_field(Category.G_1, "license_plate_vin", "không rõ")

    assert phone.uncertain is True
    assert vin.uncertain is True


def test_vietnam_license_plate_accepts_direct_user_formats() -> None:
    validator = FieldValidator()

    dashed = validator.validate_field(Category.G_1, "license_plate_vin", "30A-20865")
    compact_five_digits = validator.validate_field(Category.G_1, "license_plate_vin", "30A18397")
    compact_six_digits = validator.validate_field(Category.G_1, "license_plate_vin", "30A183974")

    assert dashed.ok is True
    assert dashed.value == "30A-20865"
    assert compact_five_digits.ok is True
    assert compact_five_digits.value == "30A-18397"
    assert compact_six_digits.ok is True
    assert compact_six_digits.value == "30A-183974"


def test_current_odo_normalizes_to_int_when_clear() -> None:
    result = FieldValidator().validate_field(Category.G_1, "current_odo", "25.000 km")

    assert result.ok is True
    assert result.value == 25000


def test_field_outside_schema_is_rejected() -> None:
    valid, uncertain, errors = FieldValidator().validate_fields(
        Category.G_3,
        {"license_plate_vin": "30A-12345", "order_phone": "0901234567"},
    )

    assert valid == {"order_phone": "0901234567"}
    assert uncertain == {}
    assert errors == ["Field 'license_plate_vin' is not allowed for G_3"]
