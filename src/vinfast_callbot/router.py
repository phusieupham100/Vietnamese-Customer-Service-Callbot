"""Intent routing for Vietnamese customer service callbot categories."""

from __future__ import annotations

from typing import Any

from .clarification import build_targeted_clarification
from .emergency_detector import EmergencyDetector
from .models import (
    CallStatus,
    Category,
    DialogueAction,
    DialogueOutput,
    RoutingResult,
    RoutingStatus,
    SessionState,
    VehicleMatchResult,
    VehicleType,
)
from .signal_extractor import InternalSignals, SignalExtractor
from .vehicle_normalizer import normalize_vehicle_text


class IntentRouter:
    """Route a turn to a category or ask a targeted clarification."""

    _AFFIRMATIVE_PHRASES = ("co", "dung", "can", "vang", "phai")
    _NEGATIVE_PHRASES = ("khong", "khong can", "khong phai", "chua can")

    def __init__(
        self,
        signal_extractor: SignalExtractor | None = None,
        emergency_detector: EmergencyDetector | None = None,
    ) -> None:
        self.emergency_detector = emergency_detector if emergency_detector is not None else EmergencyDetector()
        self.signal_extractor = signal_extractor if signal_extractor is not None else SignalExtractor(
            emergency_detector=self.emergency_detector,
        )

    def route(
        self,
        transcript: str,
        history: list[dict[str, str]] | None = None,
        current_state: SessionState | dict[str, Any] | None = None,
        vehicle_match_result: VehicleMatchResult | None = None,
    ) -> RoutingResult:
        """Route intent using the latest transcript, history, state, and vehicle match."""
        state_dict = self._state_to_dict(current_state)
        effective_history = history if history is not None else self._history_from_state(state_dict)
        signals = self.signal_extractor.extract(
            transcript=transcript,
            history=effective_history,
            state=state_dict,
            vehicle_match_result=vehicle_match_result,
        )
        emergency = self.emergency_detector.detect(transcript)
        text = normalize_vehicle_text(transcript)

        if emergency.is_emergency:
            return self._confirmed(
                Category.G_1,
                0.99,
                ["clear_emergency", *emergency.evidence],
            )

        if self._confirms_rescue(text, effective_history, state_dict):
            return self._confirmed(Category.G_1, 0.92, ["confirmed_rescue_after_clarification"])

        if signals.explicit_order_request:
            return self._confirmed(Category.G_3, 0.93, ["explicit_order_request"])

        if signals.explicit_rescue_request:
            return self._confirmed(Category.G_1, 0.94, ["explicit_rescue_request"])

        if signals.explicit_remote_support_request:
            return self._confirmed(Category.G_5, 0.9, ["explicit_remote_support_request"])

        if signals.explicit_repair_request or signals.explicit_warranty_request:
            return self._route_warranty_or_repair(signals, text, effective_history, state_dict)

        clarification = build_targeted_clarification(signals)
        return RoutingResult(
            category=None,
            routing_status=RoutingStatus.NEEDS_CLARIFICATION,
            confidence=0.55 if signals.symptom else 0.4,
            candidate_categories=clarification.candidate_categories,
            missing_discriminator=clarification.missing_discriminator,
            clarification_question=clarification.question,
            evidence=clarification.evidence,
        )

    def to_dialogue_output(
        self,
        routing_result: RoutingResult,
        emergency: bool = False,
    ) -> DialogueOutput:
        """Convert a routing result to the shared DialogueOutput contract."""
        next_action = (
            DialogueAction.HANDLE_EMERGENCY
            if emergency
            else DialogueAction.ASK_INTENT_CLARIFICATION
            if routing_result.routing_status == RoutingStatus.NEEDS_CLARIFICATION
            else DialogueAction.ASK_MISSING_FIELD
        )
        return DialogueOutput(
            response_text=routing_result.clarification_question or "",
            category=routing_result.category,
            routing_status=routing_result.routing_status,
            candidate_categories=routing_result.candidate_categories,
            pending_field=routing_result.missing_discriminator,
            next_action=next_action,
            status=CallStatus.ROUTING,
            emergency=emergency,
        )

    def _route_warranty_or_repair(
        self,
        signals: InternalSignals,
        normalized_text: str,
        history: list[dict[str, str]],
        state: dict[str, Any],
    ) -> RoutingResult:
        if signals.vehicle_type == VehicleType.MOTORBIKE.value:
            return self._confirmed(Category.G_4, 0.91, ["warranty_or_repair", "vehicle_type_motorbike"])
        if signals.vehicle_type == VehicleType.CAR.value:
            return self._confirmed(Category.G_2, 0.91, ["warranty_or_repair", "vehicle_type_car"])
        if self._rejects_rescue(normalized_text) and self._history_asked_rescue(history, state):
            return self._confirmed(
                Category.G_2,
                0.78,
                ["rejected_rescue_after_clarification", "warranty_or_repair_request"],
            )

        clarification = build_targeted_clarification(signals)
        return RoutingResult(
            category=None,
            routing_status=RoutingStatus.NEEDS_CLARIFICATION,
            confidence=0.62,
            candidate_categories=clarification.candidate_categories,
            missing_discriminator=clarification.missing_discriminator,
            clarification_question=clarification.question,
            evidence=clarification.evidence,
        )

    @staticmethod
    def _confirmed(category: Category, confidence: float, evidence: list[str]) -> RoutingResult:
        return RoutingResult(
            category=category,
            routing_status=RoutingStatus.CONFIRMED,
            confidence=confidence,
            candidate_categories=[category],
            evidence=evidence,
        )

    @classmethod
    def _confirms_rescue(
        cls,
        normalized_text: str,
        history: list[dict[str, str]],
        state: dict[str, Any],
    ) -> bool:
        if cls._rejects_rescue(normalized_text):
            return False
        if not cls._history_asked_rescue(history, state):
            return False
        return any(phrase in normalized_text for phrase in cls._AFFIRMATIVE_PHRASES)

    @classmethod
    def _rejects_rescue(cls, normalized_text: str) -> bool:
        return any(phrase in normalized_text for phrase in cls._NEGATIVE_PHRASES)

    @staticmethod
    def _history_asked_rescue(history: list[dict[str, str]], state: dict[str, Any]) -> bool:
        if state.get("pending_field") == "rescue_needed":
            return True
        if state.get("last_action") == DialogueAction.ASK_INTENT_CLARIFICATION.value:
            return state.get("pending_field") == "rescue_needed"
        for item in history:
            if item.get("role") != "assistant":
                continue
            content = normalize_vehicle_text(item.get("content", ""))
            if "cuu ho" in content and ("can" in content or "ho tro" in content):
                return True
        return False

    @staticmethod
    def _state_to_dict(current_state: SessionState | dict[str, Any] | None) -> dict[str, Any]:
        if current_state is None:
            return {}
        if isinstance(current_state, SessionState):
            return current_state.to_dict()
        return dict(current_state)

    @staticmethod
    def _history_from_state(state: dict[str, Any]) -> list[dict[str, str]]:
        history = state.get("conversation_history", [])
        if isinstance(history, list):
            return [item for item in history if isinstance(item, dict)]
        return []
