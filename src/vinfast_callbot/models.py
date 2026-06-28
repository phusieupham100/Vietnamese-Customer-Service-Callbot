"""Typed data models for the Dialogue Engine contracts.

This module mirrors `docs/01_SHARED_CONTRACTS.md`. It intentionally contains
only data containers, enum validation, and serialization helpers. Dialogue
logic, routing, extraction, ASR, TTS, and pipeline orchestration belong in later
modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


DIALOGUE_CONTRACT_VERSION = "1.0"


class Category(str, Enum):
    """Supported call categories."""

    G_1 = "G_1"
    G_2 = "G_2"
    G_3 = "G_3"
    G_4 = "G_4"
    G_5 = "G_5"


class RoutingStatus(str, Enum):
    """Routing status values from the shared contract."""

    UNRESOLVED = "unresolved"
    NEEDS_CLARIFICATION = "needs_clarification"
    CONFIRMED = "confirmed"


class CallStatus(str, Enum):
    """Call status values from the shared contract."""

    IDLE = "idle"
    ROUTING = "routing"
    COLLECTING = "collecting"
    CONFIRMING = "confirming"
    TROUBLESHOOTING = "troubleshooting"
    COMPLETED = "completed"
    PARTIAL = "partial"
    TRANSFERRED = "transferred"
    ENDED = "ended"


class DialogueAction(str, Enum):
    """Dialogue action enum from the shared contract."""

    ASK_INTENT_CLARIFICATION = "ASK_INTENT_CLARIFICATION"
    ASK_MISSING_FIELD = "ASK_MISSING_FIELD"
    CONFIRM_UNCLEAR_FIELD = "CONFIRM_UNCLEAR_FIELD"
    ACKNOWLEDGE_CORRECTION = "ACKNOWLEDGE_CORRECTION"
    PROVIDE_REMOTE_STEP = "PROVIDE_REMOTE_STEP"
    ASK_REMOTE_STEP_RESULT = "ASK_REMOTE_STEP_RESULT"
    CONFIRM_COLLECTED_INFORMATION = "CONFIRM_COLLECTED_INFORMATION"
    HANDLE_EMERGENCY = "HANDLE_EMERGENCY"
    TRANSFER_TO_HUMAN = "TRANSFER_TO_HUMAN"
    FINALIZE_CALL = "FINALIZE_CALL"
    END_PARTIAL_CALL = "END_PARTIAL_CALL"
    REPEAT_OR_REPHRASE = "REPEAT_OR_REPHRASE"


class HandoffReason(str, Enum):
    """Handoff reason enum from the shared contract."""

    EMERGENCY = "emergency"
    FAILED_UNDERSTANDING = "failed_understanding"
    OUT_OF_SCOPE = "out_of_scope"
    CUSTOMER_REQUEST = "customer_request"
    POLICY_REQUIRES_AGENT = "policy_requires_agent"
    REMOTE_FIX_FAILED = "remote_fix_failed"
    SYSTEM_ERROR = "system_error"
    RESCUE_DISPATCH = "rescue_dispatch"


class FieldStatus(str, Enum):
    """Field status enum from the shared contract."""

    MISSING = "missing"
    UNCONFIRMED = "unconfirmed"
    CONFIRMED = "confirmed"
    CORRECTED = "corrected"


class VehicleMatchType(str, Enum):
    """Vehicle matcher result type."""

    EXACT = "exact"
    ALIAS = "alias"
    FUZZY = "fuzzy"
    AMBIGUOUS = "ambiguous"
    UNKNOWN = "unknown"


class VehicleMatchStatus(str, Enum):
    """Vehicle matcher confirmation status."""

    CONFIRMED = "confirmed"
    NEEDS_CONFIRMATION = "needs_confirmation"
    UNKNOWN = "unknown"
    UNKNOWN_CONFIRMED = "unknown_confirmed"


class VehicleType(str, Enum):
    """Internal vehicle type values."""

    CAR = "car"
    MOTORBIKE = "motorbike"
    UNKNOWN = "unknown"


class PostCallEmergency(str, Enum):
    """Final post-call emergency values."""

    YES = "yes"
    NO = "no"


def _coerce_enum(value: Any, enum_type: type[Enum], field_name: str) -> Enum:
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(value)
    except ValueError as exc:
        raise ValueError(f"Invalid {field_name}: {value!r}") from exc


def _coerce_optional_enum(value: Any, enum_type: type[Enum], field_name: str) -> Enum | None:
    if value is None:
        return None
    return _coerce_enum(value, enum_type, field_name)


def _enum_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    return value


def _validate_category(value: str | Category | None, field_name: str = "category") -> Category | None:
    return _coerce_optional_enum(value, Category, field_name)  # type: ignore[return-value]


def _validate_category_list(values: list[str | Category]) -> list[Category]:
    return [_coerce_enum(value, Category, "candidate_categories") for value in values]  # type: ignore[list-item]


@dataclass(slots=True)
class DialogueInput:
    """Input object passed from voice/pipeline runtime to Dialogue Engine."""

    session_id: str
    turn_id: int
    transcript: str
    input_mode: str
    history: list[dict[str, str]] = field(default_factory=list)
    state: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.session_id:
            raise ValueError("session_id is required")
        if self.turn_id < 0:
            raise ValueError("turn_id must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "turn_id": self.turn_id,
            "transcript": self.transcript,
            "input_mode": self.input_mode,
            "history": list(self.history),
            "state": dict(self.state),
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class FieldState:
    """State metadata for a collected field."""

    value: Any = None
    status: FieldStatus | str = FieldStatus.MISSING
    source_turn: int | None = None
    confidence: float | None = None
    corrected: bool = False

    def __post_init__(self) -> None:
        self.status = _coerce_enum(self.status, FieldStatus, "field status")  # type: ignore[assignment]

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "status": _enum_value(self.status),
            "source_turn": self.source_turn,
            "confidence": self.confidence,
            "corrected": self.corrected,
        }


@dataclass(slots=True)
class DialogueOutput:
    """Per-turn output returned by the Dialogue Engine."""

    response_text: str
    category: Category | str | None = None
    routing_status: RoutingStatus | str = RoutingStatus.UNRESOLVED
    candidate_categories: list[Category | str] = field(default_factory=list)
    fields: dict[str, Any] = field(default_factory=dict)
    confirmed_fields: list[str] = field(default_factory=list)
    unconfirmed_fields: dict[str, Any] = field(default_factory=dict)
    missing_fields: list[str] = field(default_factory=list)
    pending_field: str | None = None
    next_action: DialogueAction | str = DialogueAction.REPEAT_OR_REPHRASE
    status: CallStatus | str = CallStatus.ROUTING
    failed_turn_count: int = 0
    transfer_to_human: bool = False
    handoff_reason: HandoffReason | str | None = None
    emergency: bool = False
    should_end_call: bool = False

    def __post_init__(self) -> None:
        self.category = _validate_category(self.category)
        self.routing_status = _coerce_enum(
            self.routing_status,
            RoutingStatus,
            "routing_status",
        )  # type: ignore[assignment]
        self.candidate_categories = _validate_category_list(self.candidate_categories)  # type: ignore[assignment]
        self.next_action = _coerce_enum(self.next_action, DialogueAction, "next_action")  # type: ignore[assignment]
        self.status = _coerce_enum(self.status, CallStatus, "status")  # type: ignore[assignment]
        self.handoff_reason = _coerce_optional_enum(
            self.handoff_reason,
            HandoffReason,
            "handoff_reason",
        )  # type: ignore[assignment]
        if self.failed_turn_count < 0:
            raise ValueError("failed_turn_count must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "response_text": self.response_text,
            "category": _enum_value(self.category),
            "routing_status": _enum_value(self.routing_status),
            "candidate_categories": [_enum_value(value) for value in self.candidate_categories],
            "fields": dict(self.fields),
            "confirmed_fields": list(self.confirmed_fields),
            "unconfirmed_fields": dict(self.unconfirmed_fields),
            "missing_fields": list(self.missing_fields),
            "pending_field": self.pending_field,
            "next_action": _enum_value(self.next_action),
            "status": _enum_value(self.status),
            "failed_turn_count": self.failed_turn_count,
            "transfer_to_human": self.transfer_to_human,
            "handoff_reason": _enum_value(self.handoff_reason),
            "emergency": self.emergency,
            "should_end_call": self.should_end_call,
        }


@dataclass(slots=True)
class SessionState:
    """Dialogue session state controlled by backend policy."""

    session_id: str
    turn_id: int = 0
    category: Category | str | None = None
    routing_status: RoutingStatus | str = RoutingStatus.UNRESOLVED
    candidate_categories: list[Category | str] = field(default_factory=list)
    service_goal: str = "unknown"
    fields: dict[str, Any] = field(default_factory=dict)
    field_states: dict[str, FieldState | dict[str, Any]] = field(default_factory=dict)
    confirmed_fields: list[str] = field(default_factory=list)
    unconfirmed_fields: dict[str, Any] = field(default_factory=dict)
    missing_fields: list[str] = field(default_factory=list)
    pending_field: str | None = None
    last_action: DialogueAction | str | None = None
    failed_turn_count: int = 0
    clarification_count: int = 0
    emergency: bool = False
    emergency_reason: str | None = None
    transfer_to_human: bool = False
    handoff_reason: HandoffReason | str | None = None
    status: CallStatus | str = CallStatus.IDLE
    conversation_history: list[dict[str, str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.session_id:
            raise ValueError("session_id is required")
        self.category = _validate_category(self.category)
        self.routing_status = _coerce_enum(
            self.routing_status,
            RoutingStatus,
            "routing_status",
        )  # type: ignore[assignment]
        self.candidate_categories = _validate_category_list(self.candidate_categories)  # type: ignore[assignment]
        self.last_action = _coerce_optional_enum(
            self.last_action,
            DialogueAction,
            "last_action",
        )  # type: ignore[assignment]
        self.handoff_reason = _coerce_optional_enum(
            self.handoff_reason,
            HandoffReason,
            "handoff_reason",
        )  # type: ignore[assignment]
        self.status = _coerce_enum(self.status, CallStatus, "status")  # type: ignore[assignment]

    def to_dict(self) -> dict[str, Any]:
        field_states = {
            name: value.to_dict() if isinstance(value, FieldState) else dict(value)
            for name, value in self.field_states.items()
        }
        return {
            "session_id": self.session_id,
            "turn_id": self.turn_id,
            "category": _enum_value(self.category),
            "routing_status": _enum_value(self.routing_status),
            "candidate_categories": [_enum_value(value) for value in self.candidate_categories],
            "service_goal": self.service_goal,
            "fields": dict(self.fields),
            "field_states": field_states,
            "confirmed_fields": list(self.confirmed_fields),
            "unconfirmed_fields": dict(self.unconfirmed_fields),
            "missing_fields": list(self.missing_fields),
            "pending_field": self.pending_field,
            "last_action": _enum_value(self.last_action),
            "failed_turn_count": self.failed_turn_count,
            "clarification_count": self.clarification_count,
            "emergency": self.emergency,
            "emergency_reason": self.emergency_reason,
            "transfer_to_human": self.transfer_to_human,
            "handoff_reason": _enum_value(self.handoff_reason),
            "status": _enum_value(self.status),
            "conversation_history": list(self.conversation_history),
        }


@dataclass(slots=True)
class RoutingResult:
    """Result from intent routing."""

    category: Category | str | None
    routing_status: RoutingStatus | str
    confidence: float
    candidate_categories: list[Category | str] = field(default_factory=list)
    missing_discriminator: str | None = None
    clarification_question: str | None = None
    evidence: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.category = _validate_category(self.category)
        self.routing_status = _coerce_enum(
            self.routing_status,
            RoutingStatus,
            "routing_status",
        )  # type: ignore[assignment]
        self.candidate_categories = _validate_category_list(self.candidate_categories)  # type: ignore[assignment]
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": _enum_value(self.category),
            "routing_status": _enum_value(self.routing_status),
            "confidence": self.confidence,
            "candidate_categories": [_enum_value(value) for value in self.candidate_categories],
            "missing_discriminator": self.missing_discriminator,
            "clarification_question": self.clarification_question,
            "evidence": list(self.evidence),
        }


@dataclass(slots=True)
class ExtractionResult:
    """Fields and internal signals extracted from one turn."""

    fields: dict[str, Any] = field(default_factory=dict)
    internal_signals: dict[str, Any] = field(default_factory=dict)
    uncertain_fields: dict[str, Any] = field(default_factory=dict)
    corrections: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "fields": dict(self.fields),
            "internal_signals": dict(self.internal_signals),
            "uncertain_fields": dict(self.uncertain_fields),
            "corrections": list(self.corrections),
        }


@dataclass(slots=True)
class VehicleMatchResult:
    """Internal vehicle model matching result."""

    raw_text: str
    canonical_name: str | None
    vehicle_type: VehicleType | str
    match_type: VehicleMatchType | str
    confidence: float
    status: VehicleMatchStatus | str
    candidates: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.vehicle_type = _coerce_enum(self.vehicle_type, VehicleType, "vehicle_type")  # type: ignore[assignment]
        self.match_type = _coerce_enum(self.match_type, VehicleMatchType, "match_type")  # type: ignore[assignment]
        self.status = _coerce_enum(self.status, VehicleMatchStatus, "vehicle match status")  # type: ignore[assignment]
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_text": self.raw_text,
            "canonical_name": self.canonical_name,
            "vehicle_type": _enum_value(self.vehicle_type),
            "match_type": _enum_value(self.match_type),
            "confidence": self.confidence,
            "status": _enum_value(self.status),
            "candidates": list(self.candidates),
        }


@dataclass(slots=True)
class PostCallOutput:
    """Post-call summary block in the final JSON."""

    short_summary: str
    sentimental_analysis: str
    emergency: PostCallEmergency | str

    def __post_init__(self) -> None:
        self.emergency = _coerce_enum(self.emergency, PostCallEmergency, "post_call.emergency")  # type: ignore[assignment]

    def to_dict(self) -> dict[str, Any]:
        return {
            "short_summary": self.short_summary,
            "sentimental_analysis": self.sentimental_analysis,
            "emergency": _enum_value(self.emergency),
        }


@dataclass(slots=True)
class FinalCallOutput:
    """Final JSON returned after a call completes or ends partially."""

    category: Category | str
    fields: dict[str, Any]
    post_call: PostCallOutput | dict[str, Any]

    def __post_init__(self) -> None:
        self.category = _coerce_enum(self.category, Category, "category")  # type: ignore[assignment]
        if isinstance(self.post_call, dict):
            self.post_call = PostCallOutput(**self.post_call)

    def to_dict(self) -> dict[str, Any]:
        post_call = self.post_call.to_dict() if isinstance(self.post_call, PostCallOutput) else dict(self.post_call)
        return {
            "category": _enum_value(self.category),
            "fields": dict(self.fields),
            "post_call": post_call,
        }

