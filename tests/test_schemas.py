"""Tests for category schemas."""

from __future__ import annotations

import pytest

from vinfast_callbot.models import Category
from vinfast_callbot.schemas import (
    CATEGORY_SCHEMAS,
    build_final_call_output,
    get_category_schema,
    validate_category_schemas,
)


EXPECTED_FIELDS = {
    "G_1": {
        "required": (
            "full_name",
            "phone",
            "vehicle_model",
            "license_plate_vin",
            "vehicle_type",
            "current_odo",
            "current_location",
            "city_name",
            "vehicle_condition",
        ),
        "optional": (),
    },
    "G_2": {
        "required": (
            "full_name",
            "owner_phone",
            "vehicle_model",
            "vehicle_usage_type",
            "license_plate_vin",
            "service_center",
            "vehicle_condition",
        ),
        "optional": (),
    },
    "G_3": {
        "required": (
            "full_name",
            "order_phone",
            "order_code_dealer",
            "customer_type",
        ),
        "optional": (),
    },
    "G_4": {
        "required": (
            "full_name",
            "phone",
            "vehicle_line",
            "license_plate_vin",
            "current_location",
            "vehicle_condition",
        ),
        "optional": (),
    },
    "G_5": {
        "required": (
            "full_name",
            "phone",
            "license_plate_vin",
            "vehicle_line",
            "vehicle_condition_details",
        ),
        "optional": ("current_odo",),
    },
}


def test_has_exactly_five_categories() -> None:
    validate_category_schemas()

    assert {category.value for category in CATEGORY_SCHEMAS} == {"G_1", "G_2", "G_3", "G_4", "G_5"}


@pytest.mark.parametrize("category_id,fields", EXPECTED_FIELDS.items())
def test_field_names_match_brief_exactly(category_id: str, fields: dict[str, tuple[str, ...]]) -> None:
    schema = get_category_schema(category_id)

    assert schema.required_fields == fields["required"]
    assert schema.optional_fields == fields["optional"]


def test_g5_current_odo_is_optional() -> None:
    schema = get_category_schema(Category.G_5)

    assert "current_odo" not in schema.required_fields
    assert "current_odo" in schema.optional_fields


def test_g3_does_not_have_license_plate_vin() -> None:
    schema = get_category_schema("G_3")

    assert "license_plate_vin" not in schema.required_fields
    assert "license_plate_vin" not in schema.optional_fields
    assert "license_plate_vin" not in schema.all_fields


def test_missing_final_fields_serialize_as_null() -> None:
    output = build_final_call_output(
        category="G_1",
        collected_fields={"full_name": "Nguyễn Văn Nam"},
        short_summary="Khách gọi cứu hộ nhưng chưa cung cấp đủ thông tin.",
        sentimental_analysis="urgent",
        emergency="no",
    )

    data = output.to_dict()

    assert data["fields"]["full_name"] == "Nguyễn Văn Nam"
    assert data["fields"]["phone"] is None
    assert data["fields"]["vehicle_model"] is None
    assert data["fields"]["license_plate_vin"] is None
    assert data["fields"]["current_location"] is None
    assert set(data) == {"category", "fields", "post_call"}


def test_invalid_category_lookup_is_rejected() -> None:
    with pytest.raises(ValueError, match="Invalid category"):
        get_category_schema("G_9")

