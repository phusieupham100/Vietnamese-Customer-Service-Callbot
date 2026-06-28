"""Category schemas for the Dialogue Engine.

This module mirrors `docs/02_CATEGORY_SCHEMAS.md`. Field names must remain
exactly as defined by the brief.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import Category, FinalCallOutput


@dataclass(frozen=True, slots=True)
class FieldPrompt:
    """Prompt metadata for asking one field."""

    question: str
    confirmation_required: bool = False
    description: str = ""


@dataclass(frozen=True, slots=True)
class CategorySchema:
    """Schema metadata for one call category."""

    category_id: Category
    name: str
    goal: str
    required_fields: tuple[str, ...]
    optional_fields: tuple[str, ...] = ()
    field_priority: tuple[str, ...] = ()
    completion_rule: str = ""
    field_prompts: dict[str, FieldPrompt] = field(default_factory=dict)

    @property
    def all_fields(self) -> tuple[str, ...]:
        """Return required and optional fields in final JSON order."""
        return self.required_fields + self.optional_fields

    def empty_fields(self) -> dict[str, Any]:
        """Return all final fields initialized to null/None."""
        return {field_name: None for field_name in self.all_fields}

    def build_final_fields(self, collected_fields: dict[str, Any]) -> dict[str, Any]:
        """Map collected fields to final JSON keys and fill missing values with null."""
        return {
            field_name: collected_fields.get(field_name)
            for field_name in self.all_fields
        }


COMPLETION_RULE_DEFAULT = (
    "Complete when category is confirmed and all required fields are collected, "
    "unless emergency, handoff, or partial-call policy applies."
)


CATEGORY_SCHEMAS: dict[Category, CategorySchema] = {
    Category.G_1: CategorySchema(
        category_id=Category.G_1,
        name="Cứu hộ",
        goal="Nhận báo cáo sự cố và chuẩn bị thông tin để điều phối hỗ trợ tại chỗ hoặc kéo xe.",
        required_fields=(
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
        field_priority=(
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
        completion_rule=COMPLETION_RULE_DEFAULT,
    ),
    Category.G_2: CategorySchema(
        category_id=Category.G_2,
        name="Bảo hành và sửa chữa",
        goal="Tư vấn bảo hành hoặc sửa chữa và cung cấp thông tin trung tâm dịch vụ.",
        required_fields=(
            "full_name",
            "owner_phone",
            "vehicle_model",
            "vehicle_usage_type",
            "license_plate_vin",
            "service_center",
            "vehicle_condition",
        ),
        field_priority=(
            "vehicle_condition",
            "vehicle_model",
            "vehicle_usage_type",
            "service_center",
            "owner_phone",
            "full_name",
            "license_plate_vin",
        ),
        completion_rule=COMPLETION_RULE_DEFAULT,
    ),
    Category.G_3: CategorySchema(
        category_id=Category.G_3,
        name="Đơn hàng",
        goal="Hỗ trợ trạng thái đơn hàng, giao xe, chuyển cọc hoặc cập nhật thông tin đơn.",
        required_fields=(
            "full_name",
            "order_phone",
            "order_code_dealer",
            "customer_type",
        ),
        field_priority=(
            "order_phone",
            "order_code_dealer",
            "customer_type",
            "full_name",
        ),
        completion_rule=COMPLETION_RULE_DEFAULT,
    ),
    Category.G_4: CategorySchema(
        category_id=Category.G_4,
        name="Xe máy - Bảo hành",
        goal="Tư vấn bảo hành hoặc sửa chữa xe máy điện và hướng dẫn đến trung tâm dịch vụ phù hợp.",
        required_fields=(
            "full_name",
            "phone",
            "vehicle_line",
            "license_plate_vin",
            "current_location",
            "vehicle_condition",
        ),
        field_priority=(
            "vehicle_condition",
            "vehicle_line",
            "current_location",
            "phone",
            "full_name",
            "license_plate_vin",
        ),
        completion_rule=COMPLETION_RULE_DEFAULT,
    ),
    Category.G_5: CategorySchema(
        category_id=Category.G_5,
        name="Hỗ trợ kỹ thuật từ xa",
        goal="Hướng dẫn khách kiểm tra hoặc xử lý lỗi từ xa; chuyển sang trung tâm dịch vụ nếu không giải quyết được.",
        required_fields=(
            "full_name",
            "phone",
            "license_plate_vin",
            "vehicle_line",
            "vehicle_condition_details",
        ),
        optional_fields=("current_odo",),
        field_priority=(
            "vehicle_condition_details",
            "vehicle_line",
            "phone",
            "full_name",
            "license_plate_vin",
            "current_odo",
        ),
        completion_rule=COMPLETION_RULE_DEFAULT,
    ),
}


CATEGORY_IDS = tuple(category.value for category in Category)


def get_category_schema(category: Category | str) -> CategorySchema:
    """Return schema for a category id."""
    try:
        category_id = category if isinstance(category, Category) else Category(category)
    except ValueError as exc:
        raise ValueError(f"Invalid category: {category!r}") from exc
    return CATEGORY_SCHEMAS[category_id]


def validate_category_schemas() -> None:
    """Validate internal schema consistency.

    This is intentionally small and deterministic so tests can call it directly.
    """
    expected_categories = set(Category)
    actual_categories = set(CATEGORY_SCHEMAS)
    if actual_categories != expected_categories:
        raise ValueError("CATEGORY_SCHEMAS must contain exactly G_1 through G_5")

    for schema in CATEGORY_SCHEMAS.values():
        duplicate_fields = {
            field_name
            for field_name in schema.all_fields
            if schema.all_fields.count(field_name) > 1
        }
        if duplicate_fields:
            raise ValueError(f"Duplicate fields in {schema.category_id.value}: {sorted(duplicate_fields)}")


def build_final_call_output(
    category: Category | str,
    collected_fields: dict[str, Any],
    short_summary: str = "",
    sentimental_analysis: str = "calm",
    emergency: str = "no",
) -> FinalCallOutput:
    """Build final JSON using category schema and null for missing fields."""
    schema = get_category_schema(category)
    return FinalCallOutput(
        category=schema.category_id,
        fields=schema.build_final_fields(collected_fields),
        post_call={
            "short_summary": short_summary,
            "sentimental_analysis": sentimental_analysis,
            "emergency": emergency,
        },
    )
