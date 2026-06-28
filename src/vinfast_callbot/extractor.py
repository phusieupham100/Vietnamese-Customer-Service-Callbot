"""Category-specific field extraction.

The extractor only extracts fields for an already confirmed category. It does
not merge state, ask questions, or update confirmed/unconfirmed field state.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .models import Category, ExtractionResult, VehicleMatchResult, VehicleMatchStatus, VehicleType
from .schemas import get_category_schema
from .signal_extractor import SignalExtractor
from .validators import FieldValidator
from .vehicle_catalog import VehicleModel, load_vehicle_catalog
from .vehicle_matcher import VehicleMatcher
from .vehicle_normalizer import normalize_vehicle_text


@dataclass(frozen=True, slots=True)
class _RawField:
    name: str
    value: Any
    uncertain: bool = False


class CategoryFieldExtractor:
    """Extract category-specific fields from one final transcript turn."""

    _PHONE_FIELD_BY_CATEGORY = {
        Category.G_1: "phone",
        Category.G_2: "owner_phone",
        Category.G_3: "order_phone",
        Category.G_4: "phone",
        Category.G_5: "phone",
    }
    _FULL_NAME_RE = re.compile(
        r"(?:tôi là|toi la|tên tôi là|ten toi la|mình là|minh la|anh là|anh la|chị là|chi la)\s+([^,.;]+)",
        re.IGNORECASE,
    )
    _FULL_NAME_UNICODE_RE = re.compile(
        r"(?:tôi tên là|tên tôi là|tôi là|mình là|em là|anh là|chị là)\s+([^,.;]+)",
        re.IGNORECASE,
    )
    _PENDING_FULL_NAME_PREFIX_RE = re.compile(
        r"^\s*(?:tôi tên là|tên tôi là|tôi là|mình là|em là|anh là|chị là|"
        r"toi ten la|ten toi la|toi la|minh la|em la|anh la|chi la)\s+",
        re.IGNORECASE,
    )
    _NON_NAME_WORDS = {
        "co",
        "khong",
        "vang",
        "dung",
        "sai",
        "cuu ho",
        "bao hanh",
        "sua chua",
        "vf",
        "vinfast",
        "xe",
        "bien so",
        "so dien thoai",
        "ha noi",
    }
    _PHONE_RE = re.compile(r"(?:\+?84|0)(?:[\s.\-]?\d){8,10}")
    _LICENSE_LABEL_RE = re.compile(
        r"(?:biển số|bien so|biển|bien|vin|số vin|so vin)\s*(?:là|la|:)?\s*([A-ZĐD0-9\-\s]{5,24})",
        re.IGNORECASE,
    )
    _ORDER_LABEL_RE = re.compile(
        r"(?:mã đơn|ma don|mã đơn hàng|ma don hang|đơn hàng|don hang)\s*(?:là|la|:)?\s*([A-Z0-9\-_./]{3,})",
        re.IGNORECASE,
    )
    _DEALER_RE = re.compile(r"(?:đại lý|dai ly)\s+([^,.;]+)", re.IGNORECASE)
    _ODO_RE = re.compile(
        r"(?:odo|công tơ mét|cong to met|đi được|di duoc|đã chạy|da chay|km)\s*(?:là|la|:)?\s*([0-9][0-9.,]*(?:\s*(?:km|kilomet|nghìn|nghin))?)",
        re.IGNORECASE,
    )

    def __init__(
        self,
        validator: FieldValidator | None = None,
        vehicle_matcher: VehicleMatcher | None = None,
        vehicle_models: list[VehicleModel] | None = None,
    ) -> None:
        self.validator = validator if validator is not None else FieldValidator()
        self.vehicle_matcher = vehicle_matcher if vehicle_matcher is not None else VehicleMatcher(vehicle_models)
        self.vehicle_models = vehicle_models if vehicle_models is not None else self.vehicle_matcher.models

    def extract(
        self,
        category: Category | str | None,
        transcript: str,
        existing_fields: dict[str, Any] | None = None,
        vehicle_match_result: VehicleMatchResult | None = None,
    ) -> ExtractionResult:
        """Extract fields for a confirmed category only."""
        if category is None:
            return ExtractionResult()

        schema = get_category_schema(category)
        context = existing_fields if existing_fields is not None else {}
        raw_fields = self._extract_raw_fields(schema.category_id, transcript, vehicle_match_result, context)
        allowed_names = set(schema.all_fields)
        candidate_fields = {
            raw.name: raw.value
            for raw in raw_fields
            if raw.name in allowed_names and not raw.uncertain
        }
        uncertain_fields = {
            raw.name: raw.value
            for raw in raw_fields
            if raw.name in allowed_names and raw.uncertain
        }
        fields, validation_uncertain_fields, errors = self.validator.validate_fields(schema.category_id, candidate_fields)
        uncertain_fields.update(validation_uncertain_fields)
        internal_signals: dict[str, Any] = {}
        if errors:
            internal_signals["validation_errors"] = errors
        return ExtractionResult(
            fields=fields,
            internal_signals=internal_signals,
            uncertain_fields=uncertain_fields,
            corrections=[],
        )

    def _extract_raw_fields(
        self,
        category: Category,
        transcript: str,
        vehicle_match_result: VehicleMatchResult | None,
        context: dict[str, Any],
    ) -> list[_RawField]:
        fields: list[_RawField] = []
        text = normalize_vehicle_text(transcript)

        name = self._extract_full_name(transcript)
        if name is None and self._pending_field(context) == "full_name":
            name = self._extract_pending_full_name(transcript)
        if name is not None:
            fields.append(_RawField("full_name", name))

        phone = self._extract_phone(transcript, text)
        if phone is not None:
            fields.append(_RawField(self._PHONE_FIELD_BY_CATEGORY[category], phone))

        vehicle_fields = self._extract_vehicle_fields(category, transcript, vehicle_match_result)
        fields.extend(vehicle_fields)

        license_plate_vin = self._extract_license_plate_vin(transcript, text)
        if license_plate_vin is None and self._pending_field(context) == "license_plate_vin":
            license_plate_vin = self._extract_pending_license_plate_vin(transcript)
        if license_plate_vin is not None:
            fields.append(_RawField("license_plate_vin", license_plate_vin))

        odo = self._extract_odo(transcript, text)
        if odo is not None:
            fields.append(_RawField("current_odo", odo))

        current_location = self._extract_current_location(transcript, text)
        if current_location is not None:
            fields.append(_RawField("current_location", current_location))

        city_name = self._extract_city_name(transcript, text)
        if city_name is not None:
            fields.append(_RawField("city_name", city_name))

        vehicle_condition = self._extract_vehicle_condition(category, transcript, text)
        if vehicle_condition is not None:
            target = "vehicle_condition_details" if category == Category.G_5 else "vehicle_condition"
            fields.append(_RawField(target, vehicle_condition))

        if category == Category.G_2:
            usage_type = self._extract_vehicle_usage_type(transcript, text)
            if usage_type is not None:
                fields.append(_RawField("vehicle_usage_type", usage_type))
            service_center = self._extract_service_center(transcript, text)
            if service_center is not None:
                fields.append(_RawField("service_center", service_center))

        if category == Category.G_3:
            order_code_dealer = self._extract_order_code_dealer(transcript, text)
            if order_code_dealer is not None:
                fields.append(_RawField("order_code_dealer", order_code_dealer))
            customer_type = self._extract_customer_type(transcript, text)
            if customer_type is not None:
                fields.append(_RawField("customer_type", customer_type))

        return fields

    def _extract_vehicle_fields(
        self,
        category: Category,
        transcript: str,
        vehicle_match_result: VehicleMatchResult | None,
    ) -> list[_RawField]:
        match = vehicle_match_result if vehicle_match_result is not None else self._match_vehicle_in_text(transcript)
        if match is None:
            vehicle_type = self._extract_vehicle_type_from_text(transcript)
            return [_RawField("vehicle_type", vehicle_type)] if category == Category.G_1 and vehicle_type else []

        if match.status == VehicleMatchStatus.NEEDS_CONFIRMATION or match.status == VehicleMatchStatus.UNKNOWN:
            target = self._vehicle_target_field(category)
            return [_RawField(target, match.raw_text, uncertain=True)] if target is not None else []

        value = match.canonical_name
        if not value:
            return []

        vehicle_type = _value(match.vehicle_type)
        if category == Category.G_1:
            fields = [_RawField("vehicle_model", value)]
            if vehicle_type in {VehicleType.CAR.value, VehicleType.MOTORBIKE.value}:
                fields.append(_RawField("vehicle_type", vehicle_type))
            return fields
        if category == Category.G_2 and vehicle_type == VehicleType.CAR.value:
            return [_RawField("vehicle_model", value)]
        if category == Category.G_4 and vehicle_type == VehicleType.MOTORBIKE.value:
            return [_RawField("vehicle_line", value)]
        if category == Category.G_5:
            return [_RawField("vehicle_line", value)]
        return []

    def _match_vehicle_in_text(self, transcript: str) -> VehicleMatchResult | None:
        return SignalExtractor(
            vehicle_matcher=self.vehicle_matcher,
            vehicle_models=self.vehicle_models,
        )._match_vehicle_in_text(transcript)

    @staticmethod
    def _vehicle_target_field(category: Category) -> str | None:
        if category in {Category.G_1, Category.G_2}:
            return "vehicle_model"
        if category in {Category.G_4, Category.G_5}:
            return "vehicle_line"
        return None

    @classmethod
    def _extract_full_name(cls, transcript: str) -> str | None:
        match = cls._FULL_NAME_UNICODE_RE.search(transcript) or cls._FULL_NAME_RE.search(transcript)
        if match is None:
            return None
        value = match.group(1).strip()
        value = re.split(
            r"\b(?:số|so|điện thoại|dien thoai|xe|ở|o|tại|tai|biển|bien|vin)\b",
            value,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0].strip()
        if not cls._looks_like_person_name(value):
            return None
        return value or None

    @classmethod
    def _extract_pending_full_name(cls, transcript: str) -> str | None:
        value = cls._PENDING_FULL_NAME_PREFIX_RE.sub("", transcript).strip(" ,.;:")
        if not cls._looks_like_person_name(value):
            return None
        return value

    @classmethod
    def _looks_like_person_name(cls, value: str) -> bool:
        cleaned = " ".join(value.strip().split())
        if not cleaned or re.search(r"\d", cleaned):
            return False
        if len(cleaned) < 2 or len(cleaned) > 80:
            return False
        normalized = normalize_vehicle_text(cleaned)
        if normalized.startswith(("toi o", "minh o", "dang o", "o ", "tai ")):
            return False
        if any(word in normalized for word in cls._NON_NAME_WORDS):
            return False
        return bool(re.search(r"[A-Za-zÀ-ỹĐđ]", cleaned))

    @staticmethod
    def _pending_field(context: dict[str, Any]) -> str | None:
        value = context.get("pending_field")
        return str(value) if value is not None else None

    @classmethod
    def _extract_phone(cls, transcript: str, normalized_text: str) -> str | None:
        if (
            ("so dien thoai" in normalized_text or "dien thoai" in normalized_text or "so " in normalized_text)
            and any(marker in normalized_text for marker in ("khong ro", "khong nho", "khong chac"))
        ):
            return "không rõ"
        match = cls._PHONE_RE.search(transcript)
        return match.group(0) if match is not None else None

    @classmethod
    def _extract_license_plate_vin(cls, transcript: str, normalized_text: str) -> str | None:
        if "bien so khong ro" in normalized_text or "vin khong ro" in normalized_text:
            return "không rõ"
        match = cls._LICENSE_LABEL_RE.search(transcript)
        if match is not None:
            return match.group(1).strip(" ,.;")
        return None

    @staticmethod
    def _extract_pending_license_plate_vin(transcript: str) -> str | None:
        value = transcript.strip(" ,.;:")
        if not value:
            return None
        normalized = normalize_vehicle_text(value)
        if any(marker in normalized for marker in ("khong ro", "khong nho", "khong chac")):
            return "không rõ"

        compact = re.sub(r"[\s.\-]", "", value).upper().replace("Đ", "D")
        if re.fullmatch(r"(?:[A-HJ-NPR-Z0-9]{17}|\d{2}[A-ZD]{1,2}\d{4,6})", compact):
            return value
        return None

    @classmethod
    def _extract_order_code_dealer(cls, transcript: str, normalized_text: str) -> str | None:
        if "ma don khong ro" in normalized_text:
            return "không rõ"
        match = cls._ORDER_LABEL_RE.search(transcript)
        if match is not None:
            return match.group(1).strip(" ,.;")
        dealer = cls._DEALER_RE.search(transcript)
        if dealer is not None:
            return f"đại lý {dealer.group(1).strip()}"
        return None

    @classmethod
    def _extract_odo(cls, transcript: str, normalized_text: str) -> str | None:
        if "odo khong ro" in normalized_text or "km khong ro" in normalized_text:
            return "không rõ"
        match = cls._ODO_RE.search(transcript)
        if match is not None:
            return match.group(1).strip()
        km_match = re.search(r"([0-9][0-9.,]*)\s*(?:km|kilomet)", transcript, re.IGNORECASE)
        return km_match.group(1) if km_match is not None else None

    @staticmethod
    def _extract_current_location(transcript: str, normalized_text: str) -> str | None:
        del normalized_text
        match = re.search(r"(?:đang ở|dang o|ở|tại|tai)\s+([^,.;]+)", transcript, re.IGNORECASE)
        if match is None:
            return None
        value = match.group(1).strip()
        value = re.split(r"\b(?:hà nội|ha noi|tp|thành phố|thanh pho|tỉnh|tinh)\b", value, maxsplit=1, flags=re.IGNORECASE)[0].strip()
        return value or match.group(1).strip()

    @staticmethod
    def _extract_city_name(transcript: str, normalized_text: str) -> str | None:
        city_map = {
            "ha noi": "Hà Nội",
            "ho chi minh": "Hồ Chí Minh",
            "tp hcm": "Hồ Chí Minh",
            "sai gon": "Hồ Chí Minh",
            "da nang": "Đà Nẵng",
            "hai phong": "Hải Phòng",
        }
        for normalized, display in city_map.items():
            if normalized in normalized_text:
                return display
        match = re.search(r"(?:thành phố|thanh pho|tỉnh|tinh)\s+([^,.;]+)", transcript, re.IGNORECASE)
        return match.group(1).strip() if match is not None else None

    @staticmethod
    def _extract_vehicle_condition(category: Category, transcript: str, normalized_text: str) -> str | None:
        del category
        match = re.search(
            r"(?:xe\s+)?(?:bị|bi|báo|bao|lỗi|loi|tình trạng|tinh trang)\s+([^,.;]+)",
            transcript,
            re.IGNORECASE,
        )
        if match is not None:
            return match.group(0).strip()
        for phrase in (
            "het pin",
            "chet may",
            "khong khoi dong",
            "khong di duoc",
            "treo man hinh",
            "mat ket noi",
        ):
            if phrase in normalized_text:
                return phrase
        return None

    @staticmethod
    def _extract_vehicle_usage_type(transcript: str, normalized_text: str) -> str | None:
        del transcript
        if any(value in normalized_text for value in ("ca nhan", "gia dinh")):
            return "cá nhân"
        if any(value in normalized_text for value in ("kinh doanh", "dich vu", "taxi", "cong ty")):
            return "kinh doanh"
        return None

    @staticmethod
    def _extract_service_center(transcript: str, normalized_text: str) -> str | None:
        del normalized_text
        match = re.search(r"(?:trung tâm|trung tam|xưởng|xuong)\s+([^,.;]+)", transcript, re.IGNORECASE)
        return match.group(0).strip() if match is not None else None

    @staticmethod
    def _extract_customer_type(transcript: str, normalized_text: str) -> str | None:
        del transcript
        if "doanh nghiep" in normalized_text or "cong ty" in normalized_text:
            return "doanh nghiệp"
        if "ca nhan" in normalized_text:
            return "cá nhân"
        return None

    @staticmethod
    def _extract_vehicle_type_from_text(transcript: str) -> str | None:
        text = normalize_vehicle_text(transcript)
        if "xe may dien" in text or "xe may" in text:
            return "motorbike"
        if "o to" in text or "oto" in text or "xe hoi" in text:
            return "car"
        return None


def _value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value
