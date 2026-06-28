"""Validation helpers for extracted dialogue fields.

The validators are deterministic and dependency-light. They normalize only
values that are clearly provided by the customer; unclear or malformed critical
fields are returned separately so dialogue policy can confirm them later.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from .models import CallStatus, Category
from .schemas import get_category_schema
from .vehicle_normalizer import normalize_vehicle_text


CRITICAL_FIELDS = {
    "phone",
    "owner_phone",
    "order_phone",
    "license_plate_vin",
    "order_code_dealer",
    "current_odo",
}

UNCERTAIN_MARKERS = (
    "không rõ",
    "khong ro",
    "không nhớ",
    "khong nho",
    "không chắc",
    "khong chac",
    "hình như",
    "hinh nhu",
    "có lẽ",
    "co le",
    "khoảng",
    "khoang",
    "tầm",
    "tam",
)

_PHONE_RE = re.compile(r"(?:\+?84|0)(?:[\s.\-]?\d){8,10}")
_VIN_RE = re.compile(r"\b[A-HJ-NPR-Z0-9]{17}\b", re.IGNORECASE)
_PLATE_RE = re.compile(r"\b\d{2}[A-ZĐD]{1,2}[\-\s]?\d{4,6}\b", re.IGNORECASE)
_ORDER_CODE_RE = re.compile(r"\b[A-Z0-9][A-Z0-9\-_/]{2,}\b", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class FieldValidationResult:
    """Validation result for a single extracted field."""

    field_name: str
    value: Any = None
    ok: bool = False
    uncertain: bool = False
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Generic validation result used by the JSON validator API."""

    ok: bool
    errors: list[str] = field(default_factory=list)


class FieldValidator:
    """Validate and normalize fields according to the confirmed category."""

    def validate_fields(
        self,
        category: Category | str,
        fields: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
        """Return valid fields, uncertain fields, and validation errors."""
        schema = get_category_schema(category)
        valid: dict[str, Any] = {}
        uncertain: dict[str, Any] = {}
        errors: list[str] = []

        for field_name, raw_value in fields.items():
            if field_name not in schema.all_fields:
                errors.append(f"Field {field_name!r} is not allowed for {schema.category_id.value}")
                continue

            result = self.validate_field(schema.category_id, field_name, raw_value)
            if result.ok and not result.uncertain:
                valid[field_name] = result.value
            elif result.uncertain:
                uncertain[field_name] = raw_value
            else:
                errors.extend(result.errors)

        return valid, uncertain, errors

    def validate_field(
        self,
        category: Category | str,
        field_name: str,
        raw_value: Any,
    ) -> FieldValidationResult:
        """Validate one field and normalize when safe."""
        schema = get_category_schema(category)
        if field_name not in schema.all_fields:
            return FieldValidationResult(
                field_name=field_name,
                value=raw_value,
                ok=False,
                errors=[f"Field {field_name!r} is not allowed for {schema.category_id.value}"],
            )

        if raw_value is None or str(raw_value).strip() == "":
            return FieldValidationResult(field_name=field_name, value=raw_value, ok=False, errors=["missing value"])

        if self.is_uncertain(raw_value):
            return FieldValidationResult(
                field_name=field_name,
                value=raw_value,
                ok=False,
                uncertain=field_name in CRITICAL_FIELDS,
                errors=[] if field_name in CRITICAL_FIELDS else ["uncertain value"],
            )

        if field_name in {"phone", "owner_phone", "order_phone"}:
            return self._validate_phone(field_name, str(raw_value))
        if field_name == "license_plate_vin":
            return self._validate_license_plate_or_vin(field_name, str(raw_value))
        if field_name == "order_code_dealer":
            return self._validate_order_code_dealer(field_name, str(raw_value))
        if field_name == "current_odo":
            return self._validate_current_odo(field_name, raw_value)
        if field_name == "vehicle_type":
            return self._validate_vehicle_type(field_name, str(raw_value))
        if field_name == "vehicle_usage_type":
            return self._validate_vehicle_usage_type(field_name, str(raw_value))
        if field_name == "customer_type":
            return self._validate_customer_type(field_name, str(raw_value))

        return FieldValidationResult(field_name=field_name, value=str(raw_value).strip(), ok=True)

    @staticmethod
    def is_uncertain(raw_value: Any) -> bool:
        text = normalize_vehicle_text(str(raw_value))
        return any(normalize_vehicle_text(marker) in text for marker in UNCERTAIN_MARKERS)

    @staticmethod
    def _validate_phone(field_name: str, raw_value: str) -> FieldValidationResult:
        match = _PHONE_RE.search(raw_value)
        if match is None:
            return FieldValidationResult(field_name=field_name, value=raw_value, ok=False, uncertain=True)

        digits = re.sub(r"\D", "", match.group(0))
        if digits.startswith("84"):
            digits = "0" + digits[2:]
        if len(digits) != 10 or not digits.startswith("0"):
            return FieldValidationResult(field_name=field_name, value=raw_value, ok=False, uncertain=True)
        return FieldValidationResult(field_name=field_name, value=digits, ok=True)

    @staticmethod
    def _validate_license_plate_or_vin(field_name: str, raw_value: str) -> FieldValidationResult:
        compact = re.sub(r"[\s.\-]", "", raw_value).upper()
        vin_match = _VIN_RE.search(compact)
        if vin_match is not None:
            return FieldValidationResult(field_name=field_name, value=vin_match.group(0).upper(), ok=True)

        plate_match = _PLATE_RE.search(raw_value.upper().replace("Đ", "D"))
        if plate_match is None:
            return FieldValidationResult(field_name=field_name, value=raw_value, ok=False, uncertain=True)

        plate = plate_match.group(0).upper().replace(" ", "").replace("Đ", "D")
        if "-" not in plate:
            plate = f"{plate[:3]}-{plate[3:]}"
        return FieldValidationResult(field_name=field_name, value=plate, ok=True)

    @staticmethod
    def _validate_order_code_dealer(field_name: str, raw_value: str) -> FieldValidationResult:
        value = raw_value.strip()
        normalized = normalize_vehicle_text(value)
        if "dai ly" in normalized:
            return FieldValidationResult(field_name=field_name, value=value, ok=True)

        match = _ORDER_CODE_RE.search(value)
        if match is None:
            return FieldValidationResult(field_name=field_name, value=raw_value, ok=False, uncertain=True)
        return FieldValidationResult(field_name=field_name, value=match.group(0).upper(), ok=True)

    @staticmethod
    def _validate_current_odo(field_name: str, raw_value: Any) -> FieldValidationResult:
        if isinstance(raw_value, int):
            if raw_value >= 0:
                return FieldValidationResult(field_name=field_name, value=raw_value, ok=True)
            return FieldValidationResult(field_name=field_name, value=raw_value, ok=False, uncertain=True)

        text = str(raw_value)
        normalized = normalize_vehicle_text(text)
        number_match = re.search(r"\d+(?:[.,]\d{3})*", text)
        if number_match is None:
            return FieldValidationResult(field_name=field_name, value=raw_value, ok=False, uncertain=True)

        number = int(re.sub(r"\D", "", number_match.group(0)))
        if "nghin" in normalized and number < 1000:
            number *= 1000
        return FieldValidationResult(field_name=field_name, value=number, ok=True)

    @staticmethod
    def _validate_vehicle_type(field_name: str, raw_value: str) -> FieldValidationResult:
        normalized = normalize_vehicle_text(raw_value)
        if normalized in {"car", "oto", "o to", "xe hoi"}:
            return FieldValidationResult(field_name=field_name, value="car", ok=True)
        if normalized in {"motorbike", "xe may", "xe may dien", "xe dien"}:
            return FieldValidationResult(field_name=field_name, value="motorbike", ok=True)
        return FieldValidationResult(field_name=field_name, value=raw_value, ok=False, errors=["invalid vehicle_type"])

    @staticmethod
    def _validate_vehicle_usage_type(field_name: str, raw_value: str) -> FieldValidationResult:
        normalized = normalize_vehicle_text(raw_value)
        if any(value in normalized for value in ("ca nhan", "gia dinh")):
            return FieldValidationResult(field_name=field_name, value="personal", ok=True)
        if any(value in normalized for value in ("kinh doanh", "dich vu", "taxi", "cong ty")):
            return FieldValidationResult(field_name=field_name, value="business", ok=True)
        return FieldValidationResult(field_name=field_name, value=raw_value.strip(), ok=True)

    @staticmethod
    def _validate_customer_type(field_name: str, raw_value: str) -> FieldValidationResult:
        normalized = normalize_vehicle_text(raw_value)
        if "doanh nghiep" in normalized or "cong ty" in normalized:
            return FieldValidationResult(field_name=field_name, value="business", ok=True)
        if "ca nhan" in normalized:
            return FieldValidationResult(field_name=field_name, value="personal", ok=True)
        return FieldValidationResult(field_name=field_name, value=raw_value.strip(), ok=True)


class JSONValidator:
    """Minimal JSON validator kept for pipeline-facing tests."""

    def parse_json_object(self, text: str) -> tuple[dict[str, Any] | None, list[str]]:
        """Parse a JSON object string without raising into the caller."""
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            return None, [str(exc)]
        if not isinstance(parsed, dict):
            return None, ["JSON value must be an object"]
        return parsed, []

    def validate_turn_output(self, output: dict[str, Any]) -> ValidationResult:
        """Validate basic turn-output fields used by the shared contract."""
        errors: list[str] = []
        if "response_text" not in output:
            errors.append("response_text is required")

        category = output.get("category")
        if category is not None:
            try:
                Category(category)
            except ValueError:
                errors.append(f"Invalid category: {category!r}")

        status = output.get("status")
        if status is not None:
            try:
                CallStatus(status)
            except ValueError:
                errors.append(f"Invalid status: {status!r}")

        if "fields" in output and not isinstance(output["fields"], dict):
            errors.append("fields must be an object")
        if "missing_fields" in output and not isinstance(output["missing_fields"], list):
            errors.append("missing_fields must be a list")

        return ValidationResult(ok=not errors, errors=errors)
