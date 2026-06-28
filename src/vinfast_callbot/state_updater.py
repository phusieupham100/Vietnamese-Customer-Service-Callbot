"""Session state merge logic for the Dialogue Engine.

This module updates structured state only. It intentionally does not select
dialogue actions or generate response text.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .correction_detector import CorrectionDetectionResult
from .models import (
    CallStatus,
    Category,
    ExtractionResult,
    FieldState,
    FieldStatus,
    RoutingStatus,
    SessionState,
)
from .schemas import get_category_schema
from .validators import CRITICAL_FIELDS


DEFAULT_CONFIDENCE = 0.9
UNCERTAIN_CONFIDENCE = 0.5
CONFIRMED_THRESHOLD = 0.8


@dataclass(frozen=True, slots=True)
class NoReaskMetadata:
    """Metadata describing which fields should not be asked again."""

    fields: list[str]

    def to_dict(self) -> dict[str, list[str]]:
        return {"fields": list(self.fields)}


class StateUpdater:
    """Merge extracted fields and corrections into a new SessionState."""

    def update(
        self,
        old_state: SessionState,
        category: Category | str | None = None,
        extraction_result: ExtractionResult | None = None,
        correction_result: CorrectionDetectionResult | None = None,
        field_confidences: dict[str, float] | None = None,
        turn_id: int | None = None,
    ) -> SessionState:
        """Return a new state inheriting old state and applying one turn update."""
        new_category = self._resolve_category(category, old_state.category)
        extraction = extraction_result if extraction_result is not None else ExtractionResult()
        confidences = field_confidences if field_confidences is not None else {}
        state = self._clone_state(old_state, new_category, turn_id)

        if new_category is not None:
            state = self._filter_for_category(state, new_category)

        if correction_result is not None and correction_result.is_correction:
            self._apply_fields(
                state=state,
                fields=correction_result.corrected_fields,
                confidences=correction_result.field_confidences,
                corrected=True,
            )

        self._apply_fields(
            state=state,
            fields=extraction.fields,
            confidences=confidences,
            corrected=False,
        )
        self._apply_uncertain_fields(state, extraction.uncertain_fields)
        self._refresh_missing_and_pending(state)
        return state

    def should_ask_field(self, state: SessionState, field_name: str) -> bool:
        """Return false for confirmed fields to support no-reask policy."""
        field_state = self._get_field_state(state, field_name)
        if field_state is None:
            return True
        return self._status_value(field_state.status) not in {FieldStatus.CONFIRMED.value, FieldStatus.CORRECTED.value}

    def no_reask_metadata(self, state: SessionState) -> NoReaskMetadata:
        """Return fields confirmed enough that policy should not ask again."""
        fields = [
            name
            for name, field_state in state.field_states.items()
            if self._status_value(self._as_field_state(field_state).status)
            in {FieldStatus.CONFIRMED.value, FieldStatus.CORRECTED.value}
        ]
        return NoReaskMetadata(fields=sorted(fields))

    @staticmethod
    def _resolve_category(category: Category | str | None, fallback: Category | str | None) -> Category | None:
        value = category if category is not None else fallback
        return Category(value) if value is not None else None

    def _clone_state(
        self,
        old_state: SessionState,
        category: Category | None,
        turn_id: int | None,
    ) -> SessionState:
        old = old_state.to_dict()
        return SessionState(
            session_id=old_state.session_id,
            turn_id=old_state.turn_id + 1 if turn_id is None else turn_id,
            category=category,
            routing_status=RoutingStatus.CONFIRMED if category is not None else old["routing_status"],
            candidate_categories=[] if category is not None else list(old["candidate_categories"]),
            service_goal=old["service_goal"],
            fields=dict(old["fields"]),
            field_states={name: dict(value) for name, value in old["field_states"].items()},
            confirmed_fields=list(old["confirmed_fields"]),
            unconfirmed_fields=dict(old["unconfirmed_fields"]),
            missing_fields=list(old["missing_fields"]),
            pending_field=old["pending_field"],
            last_action=old["last_action"],
            failed_turn_count=old["failed_turn_count"],
            clarification_count=old["clarification_count"],
            emergency=old["emergency"],
            emergency_reason=old["emergency_reason"],
            transfer_to_human=old["transfer_to_human"],
            handoff_reason=old["handoff_reason"],
            status=CallStatus.COLLECTING if category is not None else old["status"],
            conversation_history=list(old["conversation_history"]),
        )

    def _filter_for_category(self, state: SessionState, category: Category) -> SessionState:
        allowed = set(get_category_schema(category).all_fields)
        state.fields = {name: value for name, value in state.fields.items() if name in allowed}
        state.unconfirmed_fields = {
            name: value for name, value in state.unconfirmed_fields.items() if name in allowed
        }
        state.field_states = {
            name: value for name, value in state.field_states.items() if name in allowed
        }
        state.confirmed_fields = [
            name for name in state.confirmed_fields if name in allowed and name in state.fields
        ]
        return state

    def _apply_fields(
        self,
        state: SessionState,
        fields: dict[str, Any],
        confidences: dict[str, float],
        corrected: bool,
    ) -> None:
        if state.category is None:
            return
        allowed = set(get_category_schema(state.category).all_fields)
        for field_name, value in fields.items():
            if field_name not in allowed:
                continue
            confidence = confidences.get(field_name, DEFAULT_CONFIDENCE)
            existing = self._get_field_state(state, field_name)
            if not self._can_write(existing, confidence, corrected):
                continue

            status = FieldStatus.CORRECTED if corrected else FieldStatus.CONFIRMED
            state.fields[field_name] = value
            state.unconfirmed_fields.pop(field_name, None)
            state.field_states[field_name] = FieldState(
                value=value,
                status=status,
                source_turn=state.turn_id,
                confidence=confidence,
                corrected=corrected,
            )
            if field_name not in state.confirmed_fields:
                state.confirmed_fields.append(field_name)

    def _apply_uncertain_fields(self, state: SessionState, uncertain_fields: dict[str, Any]) -> None:
        if state.category is None:
            return
        allowed = set(get_category_schema(state.category).all_fields)
        for field_name, value in uncertain_fields.items():
            if field_name not in allowed:
                continue
            existing = self._get_field_state(state, field_name)
            if existing is not None and self._status_value(existing.status) in {
                FieldStatus.CONFIRMED.value,
                FieldStatus.CORRECTED.value,
            }:
                continue
            state.unconfirmed_fields[field_name] = value
            state.field_states[field_name] = FieldState(
                value=value,
                status=FieldStatus.UNCONFIRMED,
                source_turn=state.turn_id,
                confidence=UNCERTAIN_CONFIDENCE,
                corrected=False,
            )

    @staticmethod
    def _can_write(existing: FieldState | None, confidence: float, corrected: bool) -> bool:
        if corrected:
            return True
        if existing is None:
            return confidence >= CONFIRMED_THRESHOLD
        status = StateUpdater._status_value(existing.status)
        if status in {FieldStatus.CONFIRMED.value, FieldStatus.CORRECTED.value}:
            return False
        existing_confidence = existing.confidence or 0.0
        return confidence > existing_confidence and confidence >= CONFIRMED_THRESHOLD

    def _refresh_missing_and_pending(self, state: SessionState) -> None:
        if state.category is None:
            state.missing_fields = []
            state.pending_field = None
            return

        schema = get_category_schema(state.category)
        state.confirmed_fields = [
            name
            for name in schema.all_fields
            if name in state.fields
            and self._status_value(self._as_field_state(state.field_states[name]).status)
            in {FieldStatus.CONFIRMED.value, FieldStatus.CORRECTED.value}
        ]
        state.missing_fields = [
            name
            for name in schema.required_fields
            if name not in state.confirmed_fields and name not in state.unconfirmed_fields
        ]
        state.pending_field = self._next_pending_field(state, schema.field_priority)

    @staticmethod
    def _next_pending_field(state: SessionState, priority: tuple[str, ...]) -> str | None:
        for field_name in priority:
            if field_name in state.unconfirmed_fields:
                return field_name
        for field_name in priority:
            if field_name in state.missing_fields:
                return field_name
        return None

    def _get_field_state(self, state: SessionState, field_name: str) -> FieldState | None:
        value = state.field_states.get(field_name)
        if value is None:
            return None
        return self._as_field_state(value)

    @staticmethod
    def _as_field_state(value: FieldState | dict[str, Any]) -> FieldState:
        if isinstance(value, FieldState):
            return value
        return FieldState(**value)

    @staticmethod
    def _status_value(value: FieldStatus | str | Enum) -> str:
        return value.value if isinstance(value, Enum) else str(value)
