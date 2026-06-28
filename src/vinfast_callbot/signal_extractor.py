"""Internal signal extraction for intent routing.

This module does not choose a category and does not update final fields. It
only derives lightweight signals from the latest transcript, optional history,
optional state, and a vehicle match result.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .emergency_detector import EmergencyDetector
from .models import VehicleMatchResult, VehicleMatchStatus, VehicleType
from .vehicle_catalog import VehicleModel, load_vehicle_catalog
from .vehicle_matcher import VehicleMatcher
from .vehicle_normalizer import compact_vehicle_text, normalize_vehicle_text


@dataclass(slots=True)
class InternalSignals:
    """Routing signals extracted from one turn."""

    service_goal: str = "unknown"
    vehicle_type: str = "unknown"
    vehicle_model: str | None = None
    vehicle_model_mention: str | None = None
    symptom: str | None = None
    can_move: bool | None = None
    urgency: str = "normal"
    explicit_rescue_request: bool = False
    explicit_repair_request: bool = False
    explicit_warranty_request: bool = False
    explicit_order_request: bool = False
    explicit_remote_support_request: bool = False
    correction_detected: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "service_goal": self.service_goal,
            "vehicle_type": self.vehicle_type,
            "vehicle_model": self.vehicle_model,
            "vehicle_model_mention": self.vehicle_model_mention,
            "symptom": self.symptom,
            "can_move": self.can_move,
            "urgency": self.urgency,
            "explicit_rescue_request": self.explicit_rescue_request,
            "explicit_repair_request": self.explicit_repair_request,
            "explicit_warranty_request": self.explicit_warranty_request,
            "explicit_order_request": self.explicit_order_request,
            "explicit_remote_support_request": self.explicit_remote_support_request,
            "correction_detected": self.correction_detected,
        }


class SignalExtractor:
    """Extract conservative, rule-based routing signals."""

    _RESCUE_PHRASES = (
        "cuu ho",
        "keo xe",
        "dieu xe",
        "dieu nguoi den",
        "cho nguoi den",
        "can nguoi den",
        "ho tro tai cho",
        "toi cuu",
    )
    _REPAIR_PHRASES = (
        "sua",
        "sua chua",
        "dat lich",
        "lich kiem tra",
        "kiem tra tai trung tam",
        "mang di kiem tra",
        "mang xe di",
        "trung tam dich vu",
        "xuong dich vu",
        "bao duong",
    )
    _WARRANTY_PHRASES = (
        "bao hanh",
        "thuoc bao hanh",
        "duoc bao hanh",
    )
    _ORDER_PHRASES = (
        "don hang",
        "don xe",
        "ma don",
        "giao xe",
        "bao gio don",
        "dat coc",
        "chuyen coc",
        "dai ly",
        "khach hang doanh nghiep",
    )
    _REMOTE_ACTION_PHRASES = (
        "huong dan",
        "tu xa",
        "kiem tra truoc",
        "khac phuc truoc",
        "cach",
        "lam sao",
        "khoi dong lai",
        "reset",
        "ket noi lai",
        "thao tac",
    )
    _REMOTE_TOPIC_PHRASES = (
        "man hinh",
        "ung dung",
        "app",
        "phan mem",
        "ket noi",
        "bluetooth",
        "wifi",
        "tai khoan",
    )
    _SYMPTOM_PHRASES = (
        "het pin",
        "chet may",
        "khong khoi dong",
        "khong di duoc",
        "khong chay duoc",
        "bao loi",
        "bi loi",
        "loi",
        "treo man hinh",
        "mat ket noi",
        "khong sac duoc",
    )
    _CANNOT_MOVE_PHRASES = (
        "khong di duoc",
        "khong chay duoc",
        "khong khoi dong",
        "chet may",
        "nam duong",
        "het pin",
    )
    _URGENCY_PHRASES = (
        "ngay",
        "gap",
        "khan cap",
        "rat can",
        "lap tuc",
    )
    _CORRECTION_PHRASES = (
        "khong phai",
        "sua lai",
        "nham",
        "y toi la",
        "doi thanh",
        "so dung la",
        "thong tin dung la",
    )

    def __init__(
        self,
        vehicle_matcher: VehicleMatcher | None = None,
        vehicle_models: list[VehicleModel] | None = None,
        emergency_detector: EmergencyDetector | None = None,
    ) -> None:
        self.vehicle_matcher = vehicle_matcher if vehicle_matcher is not None else VehicleMatcher(vehicle_models)
        self.vehicle_models = vehicle_models if vehicle_models is not None else self.vehicle_matcher.models
        self.emergency_detector = emergency_detector if emergency_detector is not None else EmergencyDetector()

    def extract(
        self,
        transcript: str,
        history: list[dict[str, str]] | None = None,
        state: dict[str, Any] | None = None,
        vehicle_match_result: VehicleMatchResult | None = None,
    ) -> InternalSignals:
        """Extract internal signals without committing any field."""
        del history
        text = normalize_vehicle_text(transcript)
        match = vehicle_match_result if vehicle_match_result is not None else self._match_vehicle_in_text(transcript)
        vehicle_type = self._vehicle_type_from_match(match)
        if vehicle_type == VehicleType.UNKNOWN.value:
            vehicle_type = self._vehicle_type_from_state(state)

        explicit_rescue = self._contains_any(text, self._RESCUE_PHRASES) and not self._negates_rescue(text)
        explicit_repair = self._contains_any(text, self._REPAIR_PHRASES)
        explicit_warranty = self._contains_any(text, self._WARRANTY_PHRASES)
        explicit_order = self._contains_any(text, self._ORDER_PHRASES)
        explicit_remote = self._is_remote_support_request(text)
        symptom = self._extract_symptom(text)

        signals = InternalSignals(
            vehicle_type=vehicle_type,
            vehicle_model=self._vehicle_model_from_match(match),
            vehicle_model_mention=match.raw_text if match is not None and match.raw_text else None,
            symptom=symptom,
            can_move=False if self._contains_any(text, self._CANNOT_MOVE_PHRASES) else None,
            urgency=self._urgency(text, transcript),
            explicit_rescue_request=explicit_rescue,
            explicit_repair_request=explicit_repair,
            explicit_warranty_request=explicit_warranty,
            explicit_order_request=explicit_order,
            explicit_remote_support_request=explicit_remote,
            correction_detected=self._contains_any(text, self._CORRECTION_PHRASES),
        )
        signals.service_goal = self._service_goal(signals)
        return signals

    def _match_vehicle_in_text(self, transcript: str) -> VehicleMatchResult | None:
        normalized = normalize_vehicle_text(transcript)
        compact = compact_vehicle_text(transcript)
        mentions: list[tuple[int, str]] = []
        for model in self.vehicle_models:
            for value in (model.canonical_name, *model.aliases):
                normalized_value = normalize_vehicle_text(value)
                compact_value = compact_vehicle_text(value)
                if not normalized_value:
                    continue
                if normalized_value in normalized or compact_value in compact:
                    mentions.append((len(normalized_value), value))

        if not mentions:
            return None
        mention = sorted(mentions, reverse=True)[0][1]
        return self.vehicle_matcher.match(mention)

    @staticmethod
    def _vehicle_type_from_match(match: VehicleMatchResult | None) -> str:
        if match is None:
            return VehicleType.UNKNOWN.value
        if match.status != VehicleMatchStatus.CONFIRMED:
            return VehicleType.UNKNOWN.value
        return _enum_value(match.vehicle_type)

    @staticmethod
    def _vehicle_model_from_match(match: VehicleMatchResult | None) -> str | None:
        if match is None:
            return None
        if match.status == VehicleMatchStatus.CONFIRMED:
            return match.canonical_name
        return None

    @staticmethod
    def _vehicle_type_from_state(state: dict[str, Any] | None) -> str:
        if not state:
            return VehicleType.UNKNOWN.value
        fields = state.get("fields", {})
        for value in (state.get("vehicle_type"), fields.get("vehicle_type") if isinstance(fields, dict) else None):
            if value in (VehicleType.CAR.value, VehicleType.MOTORBIKE.value):
                return str(value)
        return VehicleType.UNKNOWN.value

    @staticmethod
    def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
        return any(phrase in text for phrase in phrases)

    @staticmethod
    def _negates_rescue(text: str) -> bool:
        return any(
            phrase in text
            for phrase in (
                "khong can cuu ho",
                "khong cuu ho",
                "chua can cuu ho",
                "khong phai cuu ho",
            )
        )

    @classmethod
    def _is_remote_support_request(cls, text: str) -> bool:
        has_action = cls._contains_any(text, cls._REMOTE_ACTION_PHRASES)
        has_topic = cls._contains_any(text, cls._REMOTE_TOPIC_PHRASES)
        return has_action and (has_topic or "kiem tra" in text or "khac phuc" in text)

    @classmethod
    def _extract_symptom(cls, text: str) -> str | None:
        for phrase in cls._SYMPTOM_PHRASES:
            if phrase in text:
                return phrase
        return None

    def _urgency(self, text: str, transcript: str) -> str:
        if self.emergency_detector.detect(transcript).is_emergency:
            return "emergency"
        if self._contains_any(text, self._URGENCY_PHRASES):
            return "urgent"
        return "normal"

    @staticmethod
    def _service_goal(signals: InternalSignals) -> str:
        if signals.explicit_order_request:
            return "order_support"
        if signals.explicit_rescue_request:
            return "rescue"
        if signals.explicit_remote_support_request:
            return "remote_support"
        if signals.explicit_repair_request or signals.explicit_warranty_request:
            if signals.vehicle_type == VehicleType.MOTORBIKE.value:
                return "motorbike_warranty"
            return "warranty_repair"
        return "unknown"


def _enum_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    return value
