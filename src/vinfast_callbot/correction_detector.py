"""Correction detection for customer-provided field updates.

The detector only identifies explicit correction turns and extracts the new
field values. It does not merge state or render acknowledgement responses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .extractor import CategoryFieldExtractor
from .models import Category, VehicleMatchResult, VehicleMatchStatus, VehicleType
from .vehicle_normalizer import normalize_vehicle_text


@dataclass(frozen=True, slots=True)
class CorrectionDetectionResult:
    """Detected correction payload for state update."""

    is_correction: bool
    corrected_fields: dict[str, Any] = field(default_factory=dict)
    field_confidences: dict[str, float] = field(default_factory=dict)
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "is_correction": self.is_correction,
            "corrected_fields": dict(self.corrected_fields),
            "field_confidences": dict(self.field_confidences),
            "evidence": list(self.evidence),
        }


class CorrectionDetector:
    """Detect explicit customer corrections such as phone or vehicle model fixes."""

    _CORRECTION_MARKERS = (
        "khong phai",
        "sua lai",
        "nham",
        "toi nham",
        "y toi la",
        "doi thanh",
        "dung la",
        "so moi la",
        "so dung la",
        "thong tin dung la",
        "xe dung la",
        "xe cua toi la",
    )

    def __init__(self, extractor: CategoryFieldExtractor | None = None) -> None:
        self.extractor = extractor if extractor is not None else CategoryFieldExtractor()

    def detect(
        self,
        transcript: str,
        category: Category | str | None,
        existing_fields: dict[str, Any] | None = None,
        vehicle_match_result: VehicleMatchResult | None = None,
    ) -> CorrectionDetectionResult:
        """Return corrected fields when the turn clearly indicates correction."""
        text = normalize_vehicle_text(transcript)
        evidence = [marker for marker in self._CORRECTION_MARKERS if marker in text]
        if not evidence or category is None:
            return CorrectionDetectionResult(False)

        extraction = self.extractor.extract(
            category=category,
            transcript=transcript,
            existing_fields=existing_fields,
            vehicle_match_result=vehicle_match_result,
        )
        corrected_fields = dict(extraction.fields)
        if vehicle_match_result is not None:
            corrected_fields.update(self._vehicle_correction_fields(Category(category), vehicle_match_result))

        if not corrected_fields:
            return CorrectionDetectionResult(False, evidence=evidence)

        return CorrectionDetectionResult(
            is_correction=True,
            corrected_fields=corrected_fields,
            field_confidences={field_name: 0.99 for field_name in corrected_fields},
            evidence=evidence,
        )

    @staticmethod
    def _vehicle_correction_fields(category: Category, match: VehicleMatchResult) -> dict[str, Any]:
        if match.status not in {VehicleMatchStatus.CONFIRMED, VehicleMatchStatus.UNKNOWN_CONFIRMED}:
            return {}
        if not match.canonical_name:
            return {}

        vehicle_type = match.vehicle_type.value if hasattr(match.vehicle_type, "value") else match.vehicle_type
        if category == Category.G_1:
            fields: dict[str, Any] = {"vehicle_model": match.canonical_name}
            if vehicle_type in {VehicleType.CAR.value, VehicleType.MOTORBIKE.value}:
                fields["vehicle_type"] = vehicle_type
            return fields
        if category == Category.G_2 and vehicle_type in {VehicleType.CAR.value, VehicleType.UNKNOWN.value}:
            return {"vehicle_model": match.canonical_name}
        if category in {Category.G_4, Category.G_5}:
            return {"vehicle_line": match.canonical_name}
        return {}
