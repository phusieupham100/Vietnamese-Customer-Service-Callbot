"""Exception handling for dialogue edge cases.

The handler returns structured results for the dialogue runtime. It does not
directly mutate SessionState and does not render natural-language responses.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .action_policy import (
    ACKNOWLEDGE_CORRECTION,
    ASK_INTENT_CLARIFICATION,
    ASK_MISSING_FIELD,
    CONFIRM_UNCLEAR_FIELD,
    CONFIRM_VEHICLE_MODEL,
    END_PARTIAL_CALL,
    HANDLE_EMERGENCY,
    REPEAT_OR_REPHRASE,
    TRANSFER_TO_HUMAN,
)
from .correction_detector import CorrectionDetectionResult
from .emergency_detector import EmergencyDetector
from .models import HandoffReason, RoutingStatus, SessionState, VehicleMatchResult, VehicleMatchStatus
from .vehicle_normalizer import normalize_vehicle_text


class ExceptionReasonCode(str, Enum):
    """Reason codes for handled dialogue exceptions."""

    MISSING_FIELD = "MISSING_FIELD"
    CUSTOMER_CORRECTION = "CUSTOMER_CORRECTION"
    AMBIGUOUS_INTENT = "AMBIGUOUS_INTENT"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    UNCLEAR_TRANSCRIPT = "UNCLEAR_TRANSCRIPT"
    UNCLEAR_FIELD = "UNCLEAR_FIELD"
    EMERGENCY_DETECTED = "EMERGENCY_DETECTED"
    FAILED_UNDERSTANDING_LIMIT = "FAILED_UNDERSTANDING_LIMIT"
    CUSTOMER_HANGUP = "CUSTOMER_HANGUP"
    CUSTOMER_REQUESTS_AGENT = "CUSTOMER_REQUESTS_AGENT"
    REMOTE_FIX_FAILED = "REMOTE_FIX_FAILED"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    UNKNOWN_VEHICLE_MODEL = "UNKNOWN_VEHICLE_MODEL"
    AMBIGUOUS_VEHICLE_MODEL = "AMBIGUOUS_VEHICLE_MODEL"


@dataclass(frozen=True, slots=True)
class ExceptionHandlerConfig:
    """Runtime configuration for exception handling."""

    emergency_hotline: str | None = None
    low_asr_confidence_threshold: float = 0.55

    @classmethod
    def from_env(cls) -> "ExceptionHandlerConfig":
        """Build config from environment variables.

        No default hotline is invented. If not configured, `emergency_hotline`
        remains None.
        """
        return cls(emergency_hotline=os.getenv("VINFAST_EMERGENCY_HOTLINE") or None)


@dataclass(frozen=True, slots=True)
class ExceptionResult:
    """Structured exception result consumed by policy/orchestration layers."""

    handled: bool
    reason_code: str | None = None
    action: str | None = None
    target_field: str | None = None
    recoverable: bool = True
    should_handoff: bool = False
    handoff_reason: str | None = None
    partial: bool = False
    state_updates: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "handled": self.handled,
            "reason_code": self.reason_code,
            "action": self.action,
            "target_field": self.target_field,
            "recoverable": self.recoverable,
            "should_handoff": self.should_handoff,
            "handoff_reason": self.handoff_reason,
            "partial": self.partial,
            "state_updates": dict(self.state_updates),
            "metadata": dict(self.metadata),
        }


class ExceptionHandler:
    """Handle the required dialogue exception cases."""

    _AGENT_REQUEST_PHRASES = (
        "gap nhan vien",
        "gap tu van vien",
        "chuyen nhan vien",
        "chuyen tu van vien",
        "nguoi that",
        "tong dai vien",
    )
    _OUT_OF_SCOPE_PHRASES = (
        "bao hiem y te",
        "mo tai khoan ngan hang",
        "dat ve may bay",
        "hoi thoi tiet",
        "mua dien thoai",
        "khong lien quan vinfast",
    )

    def __init__(
        self,
        config: ExceptionHandlerConfig | None = None,
        emergency_detector: EmergencyDetector | None = None,
    ) -> None:
        self.config = config if config is not None else ExceptionHandlerConfig.from_env()
        self.emergency_detector = emergency_detector if emergency_detector is not None else EmergencyDetector()

    def handle(
        self,
        transcript: str,
        state: SessionState,
        *,
        event_type: str | None = None,
        metadata: dict[str, Any] | None = None,
        correction_result: CorrectionDetectionResult | None = None,
        vehicle_match_result: VehicleMatchResult | None = None,
    ) -> ExceptionResult:
        """Return the first matching exception result or handled=False."""
        context = metadata or {}
        normalized = normalize_vehicle_text(transcript)

        if self._is_system_error(context):
            return self._handoff(
                ExceptionReasonCode.SYSTEM_ERROR,
                HandoffReason.SYSTEM_ERROR,
                metadata={"error_code": context.get("error_code")},
            )

        emergency = self.emergency_detector.detect(transcript)
        if emergency.is_emergency or state.emergency:
            return ExceptionResult(
                handled=True,
                reason_code=ExceptionReasonCode.EMERGENCY_DETECTED.value,
                action=HANDLE_EMERGENCY,
                recoverable=False,
                should_handoff=True,
                handoff_reason=HandoffReason.EMERGENCY.value,
                state_updates={
                    "emergency": True,
                    "emergency_reason": emergency.reason or state.emergency_reason,
                    "transfer_to_human": True,
                    "handoff_reason": HandoffReason.EMERGENCY.value,
                },
                metadata={
                    "evidence": list(emergency.evidence),
                    "emergency_hotline": self.config.emergency_hotline,
                },
            )

        if self._is_hangup(event_type, context, normalized):
            return ExceptionResult(
                handled=True,
                reason_code=ExceptionReasonCode.CUSTOMER_HANGUP.value,
                action=END_PARTIAL_CALL,
                recoverable=False,
                partial=True,
                state_updates={"status": "partial", "should_end_call": True},
            )

        vehicle_exception = self._vehicle_model_exception(vehicle_match_result)
        if vehicle_exception.handled:
            return vehicle_exception

        unclear_field = self._unclear_field(state)
        if unclear_field is not None:
            return ExceptionResult(
                handled=True,
                reason_code=ExceptionReasonCode.UNCLEAR_FIELD.value,
                action=CONFIRM_UNCLEAR_FIELD,
                target_field=unclear_field,
                state_updates={"failed_turn_count_delta": 1},
            )

        if self._is_unclear_transcript(transcript, context):
            if state.failed_turn_count + 1 >= 2:
                return self._handoff(
                    ExceptionReasonCode.FAILED_UNDERSTANDING_LIMIT,
                    HandoffReason.FAILED_UNDERSTANDING,
                    state_updates={"transfer_to_human": True},
                )
            return ExceptionResult(
                handled=True,
                reason_code=ExceptionReasonCode.UNCLEAR_TRANSCRIPT.value,
                action=REPEAT_OR_REPHRASE,
                state_updates={"failed_turn_count_delta": 1},
            )

        if correction_result is not None and correction_result.is_correction:
            return ExceptionResult(
                handled=True,
                reason_code=ExceptionReasonCode.CUSTOMER_CORRECTION.value,
                action=ACKNOWLEDGE_CORRECTION,
                metadata={
                    "corrected_fields": sorted(correction_result.corrected_fields),
                    "evidence": list(correction_result.evidence),
                },
            )

        if self._customer_requests_agent(normalized):
            return self._handoff(ExceptionReasonCode.CUSTOMER_REQUESTS_AGENT, HandoffReason.CUSTOMER_REQUEST)

        if self._remote_fix_failed(state, context, normalized):
            return self._handoff(ExceptionReasonCode.REMOTE_FIX_FAILED, HandoffReason.REMOTE_FIX_FAILED)

        if state.failed_turn_count >= 2:
            return self._handoff(
                ExceptionReasonCode.FAILED_UNDERSTANDING_LIMIT,
                HandoffReason.FAILED_UNDERSTANDING,
                state_updates={"transfer_to_human": True},
            )

        if self._out_of_scope(context, normalized):
            return self._handoff(
                ExceptionReasonCode.OUT_OF_SCOPE,
                HandoffReason.OUT_OF_SCOPE,
                metadata={"redirect": context.get("redirect_category")},
            )

        if self._ambiguous_intent(state):
            return ExceptionResult(
                handled=True,
                reason_code=ExceptionReasonCode.AMBIGUOUS_INTENT.value,
                action=ASK_INTENT_CLARIFICATION,
                target_field=state.pending_field,
                state_updates={"routing_status": RoutingStatus.NEEDS_CLARIFICATION.value},
            )

        missing_field = self._missing_field(state)
        if missing_field is not None:
            return ExceptionResult(
                handled=True,
                reason_code=ExceptionReasonCode.MISSING_FIELD.value,
                action=ASK_MISSING_FIELD,
                target_field=missing_field,
            )

        return ExceptionResult(handled=False)

    @staticmethod
    def _is_system_error(metadata: dict[str, Any]) -> bool:
        return bool(metadata.get("system_error") or metadata.get("error_code") == "INTERNAL_DIALOGUE_ERROR")

    @staticmethod
    def _is_hangup(event_type: str | None, metadata: dict[str, Any], normalized_text: str) -> bool:
        return (
            event_type == "hangup"
            or metadata.get("event_type") == "hangup"
            or "goi lai sau" in normalized_text
            or "toi tat may" in normalized_text
        )

    def _vehicle_model_exception(self, match: VehicleMatchResult | None) -> ExceptionResult:
        if match is None:
            return ExceptionResult(handled=False)
        status = match.status.value if hasattr(match.status, "value") else str(match.status)
        match_type = match.match_type.value if hasattr(match.match_type, "value") else str(match.match_type)
        if status == VehicleMatchStatus.NEEDS_CONFIRMATION.value:
            reason = (
                ExceptionReasonCode.AMBIGUOUS_VEHICLE_MODEL
                if match_type == "ambiguous"
                else ExceptionReasonCode.UNKNOWN_VEHICLE_MODEL
            )
            return ExceptionResult(
                handled=True,
                reason_code=reason.value,
                action=CONFIRM_VEHICLE_MODEL,
                target_field="vehicle_model",
                metadata={
                    "raw_text": match.raw_text,
                    "candidates": list(match.candidates),
                    "match_type": match_type,
                    "status": status,
                },
            )
        if status == VehicleMatchStatus.UNKNOWN.value:
            return ExceptionResult(
                handled=True,
                reason_code=ExceptionReasonCode.UNKNOWN_VEHICLE_MODEL.value,
                action=CONFIRM_VEHICLE_MODEL,
                target_field="vehicle_model",
                metadata={
                    "raw_text": match.raw_text,
                    "candidates": [],
                    "match_type": match_type,
                    "status": status,
                },
            )
        return ExceptionResult(handled=False)

    @staticmethod
    def _unclear_field(state: SessionState) -> str | None:
        if state.pending_field in state.unconfirmed_fields:
            return state.pending_field
        for field_name in ("phone", "owner_phone", "order_phone", "license_plate_vin", "order_code_dealer", "current_odo"):
            if field_name in state.unconfirmed_fields:
                return field_name
        return None

    def _is_unclear_transcript(self, transcript: str, metadata: dict[str, Any]) -> bool:
        if not transcript.strip():
            return True
        confidence = metadata.get("asr_confidence")
        if isinstance(confidence, (int, float)) and confidence < self.config.low_asr_confidence_threshold:
            return True
        normalized = normalize_vehicle_text(transcript)
        return normalized in {"khong nghe ro", "em nghe khong ro", "a a", "um", "uh"}

    @classmethod
    def _customer_requests_agent(cls, normalized_text: str) -> bool:
        return any(phrase in normalized_text for phrase in cls._AGENT_REQUEST_PHRASES)

    @staticmethod
    def _remote_fix_failed(state: SessionState, metadata: dict[str, Any], normalized_text: str) -> bool:
        if metadata.get("remote_fix_failed"):
            return True
        troubleshooting = state.fields.get("troubleshooting")
        if isinstance(troubleshooting, dict) and troubleshooting.get("failed"):
            return True
        return "van khong duoc" in normalized_text or "khong khac phuc duoc" in normalized_text

    @classmethod
    def _out_of_scope(cls, metadata: dict[str, Any], normalized_text: str) -> bool:
        return bool(metadata.get("out_of_scope")) or any(phrase in normalized_text for phrase in cls._OUT_OF_SCOPE_PHRASES)

    @staticmethod
    def _ambiguous_intent(state: SessionState) -> bool:
        status = state.routing_status.value if hasattr(state.routing_status, "value") else state.routing_status
        return state.category is None or status == RoutingStatus.NEEDS_CLARIFICATION.value

    @staticmethod
    def _missing_field(state: SessionState) -> str | None:
        if state.category is None:
            return None
        if state.pending_field in state.missing_fields:
            return state.pending_field
        return state.missing_fields[0] if state.missing_fields else None

    @staticmethod
    def _handoff(
        reason_code: ExceptionReasonCode,
        handoff_reason: HandoffReason,
        state_updates: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ExceptionResult:
        updates = {"transfer_to_human": True, "handoff_reason": handoff_reason.value}
        if state_updates:
            updates.update(state_updates)
        return ExceptionResult(
            handled=True,
            reason_code=reason_code.value,
            action=TRANSFER_TO_HUMAN,
            recoverable=False,
            should_handoff=True,
            handoff_reason=handoff_reason.value,
            state_updates=updates,
            metadata=metadata or {},
        )
