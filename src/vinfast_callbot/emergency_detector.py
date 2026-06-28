"""Emergency detection for the Dialogue Engine.

The detector is intentionally conservative. Vehicle symptoms such as a dead
battery or failure to start are not emergencies unless the customer also gives
clear danger evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .vehicle_normalizer import normalize_vehicle_text


@dataclass(frozen=True, slots=True)
class EmergencyDetection:
    """Internal emergency detection result."""

    is_emergency: bool
    reason: str | None = None
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "is_emergency": self.is_emergency,
            "reason": self.reason,
            "evidence": list(self.evidence),
        }


class EmergencyDetector:
    """Detect clear danger that should preempt normal routing."""

    _FIRE_PHRASES = (
        "dang chay",
        "boc chay",
        "chay xe",
        "xe chay",
        "boc khoi",
        "co khoi",
        "mui khet",
    )
    _INJURY_PHRASES = (
        "bi thuong",
        "nguoi bi thuong",
        "co nguoi bi thuong",
        "thuong vong",
        "cap cuu",
        "bat tinh",
    )
    _ACCIDENT_PHRASES = (
        "tai nan",
        "va cham",
        "dam xe",
        "lat xe",
        "tong xe",
    )
    _DANGER_PHRASES = (
        "nguy hiem",
        "ket trong xe",
        "khong thoat ra duoc",
        "nguy co tai nan",
        "sap no",
    )

    def detect(self, transcript: str) -> EmergencyDetection:
        """Return emergency status for one user transcript."""
        text = normalize_vehicle_text(transcript)
        evidence: list[str] = []

        fire = self._first_match(text, self._FIRE_PHRASES)
        if fire is not None:
            evidence.append(fire)
            return EmergencyDetection(True, "fire_or_smoke", evidence)

        injury = self._first_match(text, self._INJURY_PHRASES)
        accident = self._first_match(text, self._ACCIDENT_PHRASES)
        danger = self._first_match(text, self._DANGER_PHRASES)

        if injury is not None:
            evidence.append(injury)
        if accident is not None:
            evidence.append(accident)
        if danger is not None:
            evidence.append(danger)

        if injury is not None and (accident is not None or danger is not None):
            return EmergencyDetection(True, "accident_with_injury", evidence)
        if accident is not None and danger is not None:
            return EmergencyDetection(True, "dangerous_accident", evidence)

        return EmergencyDetection(False)

    @classmethod
    def is_emergency(cls, transcript: str) -> bool:
        """Convenience boolean API for tests and simple callers."""
        return cls().detect(transcript).is_emergency

    @staticmethod
    def _first_match(text: str, phrases: tuple[str, ...]) -> str | None:
        for phrase in phrases:
            if phrase in text:
                return phrase
        return None
