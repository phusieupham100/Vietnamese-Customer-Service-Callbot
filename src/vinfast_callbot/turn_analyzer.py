"""LLM-first semantic turn analysis for the Dialogue Engine."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .llm_client import LLMClient, LLMClientError, OpenAIAPIClient
from .models import Category, DialogueInput, RoutingStatus, SessionState
from .schemas import CATEGORY_SCHEMAS


class TurnAnalysisError(RuntimeError):
    """Raised when the LLM analyzer cannot produce valid structured JSON."""


@dataclass(frozen=True, slots=True)
class EmergencyAnalysis:
    """Semantic emergency assessment returned by the LLM."""

    is_emergency: bool = False
    severity: str = "none"
    reason: str | None = None
    requires_immediate_handoff: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "EmergencyAnalysis":
        if not isinstance(data, dict):
            return cls()
        return cls(
            is_emergency=bool(data.get("is_emergency", False)),
            severity=str(data.get("severity") or "none"),
            reason=str(data["reason"]) if data.get("reason") else None,
            requires_immediate_handoff=bool(data.get("requires_immediate_handoff", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_emergency": self.is_emergency,
            "severity": self.severity,
            "reason": self.reason,
            "requires_immediate_handoff": self.requires_immediate_handoff,
        }


@dataclass(frozen=True, slots=True)
class TurnAnalysisResult:
    """Structured semantic understanding result for one user turn."""

    understood: bool
    user_goal: str = "unknown"
    category: Category | None = None
    routing_status: RoutingStatus = RoutingStatus.UNRESOLVED
    candidate_categories: list[Category] = field(default_factory=list)
    pending_field: str | None = None
    emergency: EmergencyAnalysis = field(default_factory=EmergencyAnalysis)
    fields: dict[str, Any] = field(default_factory=dict)
    uncertain_fields: dict[str, Any] = field(default_factory=dict)
    corrections: list[dict[str, Any]] = field(default_factory=list)
    ambiguities: list[str] = field(default_factory=list)
    intent_switch: bool = False
    out_of_scope: bool = False
    handoff_reason: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)
    log: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any], log: dict[str, Any] | None = None) -> "TurnAnalysisResult":
        """Validate and coerce LLM JSON into typed internal data."""
        category = _optional_category(data.get("category"))
        routing_status = _routing_status(data.get("routing_status"))
        candidates = [_category(value) for value in data.get("candidate_categories", []) if value is not None]
        fields = data.get("fields") if isinstance(data.get("fields"), dict) else {}
        uncertain = data.get("uncertain_fields") if isinstance(data.get("uncertain_fields"), dict) else {}
        corrections = data.get("corrections") if isinstance(data.get("corrections"), list) else []
        ambiguities = data.get("ambiguities") if isinstance(data.get("ambiguities"), list) else []
        return cls(
            understood=bool(data.get("understood", False)),
            user_goal=str(data.get("user_goal") or "unknown"),
            category=category,
            routing_status=routing_status,
            candidate_categories=candidates,
            pending_field=str(data["pending_field"]) if data.get("pending_field") else None,
            emergency=EmergencyAnalysis.from_dict(data.get("emergency")),
            fields={str(key): value for key, value in fields.items()},
            uncertain_fields={str(key): value for key, value in uncertain.items()},
            corrections=[dict(item) for item in corrections if isinstance(item, dict)],
            ambiguities=[str(item) for item in ambiguities],
            intent_switch=bool(data.get("intent_switch", False)),
            out_of_scope=bool(data.get("out_of_scope", False)),
            handoff_reason=str(data["handoff_reason"]) if data.get("handoff_reason") else None,
            raw=dict(data),
            log=log or {},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "understood": self.understood,
            "user_goal": self.user_goal,
            "category": self.category.value if isinstance(self.category, Enum) else self.category,
            "routing_status": self.routing_status.value,
            "candidate_categories": [category.value for category in self.candidate_categories],
            "pending_field": self.pending_field,
            "emergency": self.emergency.to_dict(),
            "fields": dict(self.fields),
            "uncertain_fields": dict(self.uncertain_fields),
            "corrections": list(self.corrections),
            "ambiguities": list(self.ambiguities),
            "intent_switch": self.intent_switch,
            "out_of_scope": self.out_of_scope,
            "handoff_reason": self.handoff_reason,
        }


class LLMTurnAnalyzer:
    """Use a real LLM as the primary semantic understanding backend."""

    def __init__(self, llm_client: LLMClient | None = None, max_attempts: int = 2) -> None:
        self.llm_client = llm_client if llm_client is not None else OpenAIAPIClient()
        self.max_attempts = max(1, max_attempts)

    def analyze(self, dialogue_input: DialogueInput, state: SessionState) -> TurnAnalysisResult:
        """Analyze one turn through the LLM and return structured JSON."""
        messages = self._messages(dialogue_input, state)
        last_error: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            log = {
                "turn_analyzer_backend": "llm",
                "llm_called": True,
                "llm_attempt": attempt,
                "llm_parse_success": False,
                "rule_fallback_used": False,
            }
            try:
                content = self.llm_client.chat(messages)
                parsed = _parse_json_object(content)
                log["llm_parse_success"] = True
                return TurnAnalysisResult.from_dict(parsed, log=log)
            except (LLMClientError, TurnAnalysisError, ValueError, TypeError, json.JSONDecodeError) as exc:
                last_error = exc
                log["llm_error"] = str(exc)
                messages = messages + [
                    {
                        "role": "user",
                        "content": "Previous output was invalid. Return exactly one valid JSON object following the schema.",
                    }
                ]
        raise TurnAnalysisError(f"LLM turn analysis failed after retry: {last_error}") from last_error

    def _messages(self, dialogue_input: DialogueInput, state: SessionState) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": TURN_ANALYZER_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(self._payload(dialogue_input, state), ensure_ascii=False)},
        ]

    @staticmethod
    def _payload(dialogue_input: DialogueInput, state: SessionState) -> dict[str, Any]:
        schemas = {
            category.value: {
                "required_fields": list(schema.required_fields),
                "optional_fields": list(schema.optional_fields),
                "field_priority": list(schema.field_priority),
            }
            for category, schema in CATEGORY_SCHEMAS.items()
        }
        return {
            "latest_transcript": dialogue_input.transcript,
            "history": dialogue_input.history or state.conversation_history,
            "current_state": state.to_dict(),
            "pending_field": state.pending_field,
            "category_schema": schemas,
            "metadata": dict(dialogue_input.metadata),
        }


TURN_ANALYZER_SYSTEM_PROMPT = """\
You are the LLM Turn Analyzer for a Vietnamese VinFast customer-service callbot.
Understand the latest transcript semantically using the whole conversation
history, current state, pending_field, and category schema. Do not rely on a
single keyword. Return exactly one JSON object and no markdown.

Responsibilities:
- infer user_goal and category;
- assess emergency from real-world safety risk, not from ordinary vehicle fault words;
- extract natural full_name, current_location, city_name, vehicle_condition, service_center, customer_type, usage type;
- detect correction and intent switch;
- use pending_field to understand short answers such as names, yes/no, phone, plate, or location;
- never invent a field the customer did not provide.

Routing rules:
- G_1 only when customer clearly needs rescue/towing/on-site help, confirms rescue, or real emergency exists.
- Do not route G_1 only because the vehicle has no battery, cannot start, is broken, or has an error.
- G_2 is car warranty/repair/service-center support.
- G_3 is order/deposit/delivery/dealer/order-status support.
- G_4 is motorbike warranty/repair support.
- G_5 is remote troubleshooting or how-to guidance.
- If intent is unclear, category must be null and routing_status must be needs_clarification.

Emergency rules:
- emergency=true only for actual safety risk such as serious crash, injury, trapped people, fire/smoke, or dangerous road position.
- Ordinary cases like "xe không khởi động", "xe hết pin", or "màn hình bị treo" are not emergency by themselves.

JSON schema:
{
  "understood": true,
  "user_goal": "request_emergency_rescue|request_rescue|warranty_repair|order_support|motorbike_warranty|remote_support|unknown|out_of_scope",
  "category": "G_1|G_2|G_3|G_4|G_5|null",
  "routing_status": "unresolved|needs_clarification|confirmed",
  "candidate_categories": ["G_1"],
  "pending_field": "field_or_discriminator_or_null",
  "emergency": {
    "is_emergency": false,
    "severity": "none|low|medium|high",
    "reason": null,
    "requires_immediate_handoff": false
  },
  "fields": {},
  "uncertain_fields": {},
  "corrections": [
    {"field": "vehicle_model", "value": "VF9", "confidence": 0.99, "reason": "customer corrected previous model"}
  ],
  "ambiguities": [],
  "intent_switch": false,
  "out_of_scope": false,
  "handoff_reason": null
}
"""


def _parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError as exc:
        match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
        if match is None:
            raise TurnAnalysisError("LLM output did not contain a JSON object") from exc
        value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise TurnAnalysisError("LLM output must be a JSON object")
    return value


def _optional_category(value: Any) -> Category | None:
    if value in (None, "", "null"):
        return None
    return _category(value)


def _category(value: Any) -> Category:
    try:
        return Category(str(value))
    except ValueError as exc:
        raise TurnAnalysisError(f"Invalid category from LLM: {value!r}") from exc


def _routing_status(value: Any) -> RoutingStatus:
    if value in (None, ""):
        return RoutingStatus.UNRESOLVED
    try:
        return RoutingStatus(str(value))
    except ValueError as exc:
        raise TurnAnalysisError(f"Invalid routing_status from LLM: {value!r}") from exc
