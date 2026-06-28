"""Dialogue action policy.

This module chooses structured actions only. It does not generate natural
language responses and does not mutate session state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .correction_detector import CorrectionDetectionResult
from .models import Category, FieldState, FieldStatus, RoutingStatus, SessionState
from .schemas import get_category_schema
from .validators import CRITICAL_FIELDS


ASK_INTENT_CLARIFICATION = "ASK_INTENT_CLARIFICATION"
ASK_MISSING_FIELD = "ASK_MISSING_FIELD"
CONFIRM_UNCLEAR_FIELD = "CONFIRM_UNCLEAR_FIELD"
CONFIRM_VEHICLE_MODEL = "CONFIRM_VEHICLE_MODEL"
ACKNOWLEDGE_CORRECTION = "ACKNOWLEDGE_CORRECTION"
PROVIDE_REMOTE_STEP = "PROVIDE_REMOTE_STEP"
ASK_REMOTE_STEP_RESULT = "ASK_REMOTE_STEP_RESULT"
CONFIRM_COLLECTED_INFORMATION = "CONFIRM_COLLECTED_INFORMATION"
HANDLE_EMERGENCY = "HANDLE_EMERGENCY"
TRANSFER_TO_HUMAN = "TRANSFER_TO_HUMAN"
FINALIZE_CALL = "FINALIZE_CALL"
END_PARTIAL_CALL = "END_PARTIAL_CALL"
REPEAT_OR_REPHRASE = "REPEAT_OR_REPHRASE"

SUPPORTED_ACTIONS = {
    ASK_INTENT_CLARIFICATION,
    ASK_MISSING_FIELD,
    CONFIRM_UNCLEAR_FIELD,
    CONFIRM_VEHICLE_MODEL,
    ACKNOWLEDGE_CORRECTION,
    PROVIDE_REMOTE_STEP,
    ASK_REMOTE_STEP_RESULT,
    CONFIRM_COLLECTED_INFORMATION,
    HANDLE_EMERGENCY,
    TRANSFER_TO_HUMAN,
    FINALIZE_CALL,
    END_PARTIAL_CALL,
    REPEAT_OR_REPHRASE,
}

VEHICLE_MODEL_FIELDS = {"vehicle_model", "vehicle_line"}


@dataclass(frozen=True, slots=True)
class ActionDecision:
    """Structured policy action for the response/action layer."""

    action: str
    target_field: str | None = None
    reason: str = ""
    category: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.action not in SUPPORTED_ACTIONS:
            raise ValueError(f"Unsupported action: {self.action!r}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "target_field": self.target_field,
            "reason": self.reason,
            "category": self.category,
            "metadata": dict(self.metadata),
        }


class DialogueActionPolicy:
    """Choose the next structured action using documented priority order."""

    def decide(
        self,
        state: SessionState,
        correction_result: CorrectionDetectionResult | None = None,
        event_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ActionDecision:
        """Return the next action without rendering response text."""
        context = metadata or {}

        if state.emergency:
            emergency_field = self._next_emergency_field(state)
            return self._decision(
                HANDLE_EMERGENCY,
                state,
                target_field=emergency_field,
                reason="emergency",
                metadata={"collecting_emergency_field": emergency_field} if emergency_field else {},
            )

        if self._is_hangup(event_type, context):
            return self._decision(END_PARTIAL_CALL, state, reason="hangup")

        if not self._category_confirmed(state):
            return self._decision(
                ASK_INTENT_CLARIFICATION,
                state,
                target_field=state.pending_field,
                reason="category_not_confirmed",
            )

        if correction_result is not None and correction_result.is_correction:
            return self._decision(
                ACKNOWLEDGE_CORRECTION,
                state,
                reason="customer_correction",
                metadata={"corrected_fields": sorted(correction_result.corrected_fields)},
            )

        unclear_field = self._next_unclear_field(state)
        if unclear_field is not None:
            if self._is_vehicle_model_confirmation(state, unclear_field, context):
                return self._decision(
                    CONFIRM_VEHICLE_MODEL,
                    state,
                    target_field=unclear_field,
                    reason="vehicle_model_unclear",
                    metadata=self._vehicle_metadata(state, unclear_field, context),
                )
            return self._decision(
                CONFIRM_UNCLEAR_FIELD,
                state,
                target_field=unclear_field,
                reason="critical_or_unclear_field",
            )

        if state.transfer_to_human or state.failed_turn_count >= 2:
            return self._decision(TRANSFER_TO_HUMAN, state, reason="handoff_required")

        missing_field = self._next_missing_field(state)
        if missing_field is not None:
            return self._decision(
                ASK_MISSING_FIELD,
                state,
                target_field=missing_field,
                reason="required_field_missing",
            )

        if self._is_g5_unresolved(state):
            return self._g5_troubleshooting_action(state)

        if self._needs_final_confirmation(state):
            return self._decision(CONFIRM_COLLECTED_INFORMATION, state, reason="ready_for_final_confirmation")

        return self._decision(FINALIZE_CALL, state, reason="ready_to_finalize")

    @staticmethod
    def _decision(
        action: str,
        state: SessionState,
        target_field: str | None = None,
        reason: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> ActionDecision:
        category = state.category.value if hasattr(state.category, "value") else state.category
        return ActionDecision(
            action=action,
            target_field=target_field,
            reason=reason,
            category=category,
            metadata=metadata or {},
        )

    @staticmethod
    def _is_hangup(event_type: str | None, metadata: dict[str, Any]) -> bool:
        return event_type == "hangup" or metadata.get("event_type") == "hangup"

    @staticmethod
    def _category_confirmed(state: SessionState) -> bool:
        if state.category is None:
            return False
        status = state.routing_status.value if hasattr(state.routing_status, "value") else state.routing_status
        return status != RoutingStatus.NEEDS_CLARIFICATION.value

    def _next_unclear_field(self, state: SessionState) -> str | None:
        if not state.unconfirmed_fields:
            return None
        if state.pending_field in state.unconfirmed_fields:
            return state.pending_field

        for field_name in self._field_priority(state):
            if field_name in state.unconfirmed_fields:
                return field_name
        for field_name in CRITICAL_FIELDS:
            if field_name in state.unconfirmed_fields:
                return field_name
        return next(iter(state.unconfirmed_fields))

    def _next_missing_field(self, state: SessionState) -> str | None:
        if not self._category_confirmed(state) or not state.category:
            return None
        if state.pending_field in state.missing_fields and not self._is_confirmed(state, state.pending_field):
            return state.pending_field

        for field_name in self._field_priority(state):
            if field_name in state.missing_fields and not self._is_confirmed(state, field_name):
                return field_name
        for field_name in state.missing_fields:
            if not self._is_confirmed(state, field_name):
                return field_name
        return None

    @staticmethod
    def _is_vehicle_model_confirmation(
        state: SessionState,
        field_name: str,
        metadata: dict[str, Any],
    ) -> bool:
        if field_name in VEHICLE_MODEL_FIELDS:
            return True
        vehicle_state = metadata.get("vehicle_model_state") or state.fields.get("vehicle_model_state")
        if isinstance(vehicle_state, dict):
            status = vehicle_state.get("status")
            return status in {"needs_confirmation", "unknown"}
        return False

    @staticmethod
    def _vehicle_metadata(
        state: SessionState,
        field_name: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        vehicle_state = metadata.get("vehicle_model_state") or state.fields.get("vehicle_model_state")
        result: dict[str, Any] = {"field": field_name}
        if isinstance(vehicle_state, dict):
            result["vehicle_model_state"] = dict(vehicle_state)
        return result

    @staticmethod
    def _is_confirmed(state: SessionState, field_name: str | None) -> bool:
        if field_name is None:
            return False
        field_state = state.field_states.get(field_name)
        if field_state is None:
            return field_name in state.confirmed_fields
        state_obj = field_state if isinstance(field_state, FieldState) else FieldState(**field_state)
        status = state_obj.status.value if isinstance(state_obj.status, Enum) else str(state_obj.status)
        return status in {FieldStatus.CONFIRMED.value, FieldStatus.CORRECTED.value}

    @staticmethod
    def _field_priority(state: SessionState) -> tuple[str, ...]:
        if state.category is None:
            return ()
        return get_category_schema(state.category).field_priority

    def _next_emergency_field(self, state: SessionState) -> str | None:
        if state.category is None:
            return None
        emergency_priority = (
            "current_location",
            "city_name",
            "phone",
            "full_name",
            "vehicle_condition",
            "vehicle_model",
            "license_plate_vin",
            "vehicle_type",
            "current_odo",
        )
        for field_name in emergency_priority:
            if field_name in state.missing_fields and not self._is_confirmed(state, field_name):
                return field_name
        return self._next_missing_field(state)

    def _is_g5_unresolved(self, state: SessionState) -> bool:
        category = state.category.value if hasattr(state.category, "value") else state.category
        if category != Category.G_5.value:
            return False
        troubleshooting = self._troubleshooting(state)
        return bool(troubleshooting) and not troubleshooting.get("resolved", False)

    def _g5_troubleshooting_action(self, state: SessionState) -> ActionDecision:
        troubleshooting = self._troubleshooting(state)
        steps_attempted = troubleshooting.get("steps_attempted", [])
        max_steps = int(troubleshooting.get("max_steps", 2))
        awaiting_result = troubleshooting.get("awaiting_result", False)

        if awaiting_result:
            return self._decision(ASK_REMOTE_STEP_RESULT, state, reason="awaiting_remote_step_result")
        if isinstance(steps_attempted, list) and len(steps_attempted) >= max_steps:
            return self._decision(TRANSFER_TO_HUMAN, state, reason="remote_support_unresolved")
        return self._decision(PROVIDE_REMOTE_STEP, state, reason="provide_next_remote_step")

    @staticmethod
    def _troubleshooting(state: SessionState) -> dict[str, Any]:
        value = state.fields.get("troubleshooting")
        return dict(value) if isinstance(value, dict) else {}

    @staticmethod
    def _needs_final_confirmation(state: SessionState) -> bool:
        return not state.fields.get("_final_confirmation_done", False)
