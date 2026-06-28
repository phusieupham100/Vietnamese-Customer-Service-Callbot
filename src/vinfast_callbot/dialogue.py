"""Dialogue orchestrator connecting routing, extraction, state, policy, and rendering.

The orchestrator is intentionally thin: detailed business rules remain in the
module-specific classes. It has no ASR, microphone, TTS, or evaluation runtime
dependency.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

from .action_policy import (
    CONFIRM_VEHICLE_MODEL,
    END_PARTIAL_CALL,
    REPEAT_OR_REPHRASE,
    TRANSFER_TO_HUMAN,
    ActionDecision,
    DialogueActionPolicy,
)
from .correction_detector import CorrectionDetectionResult
from .models import (
    CallStatus,
    Category,
    DialogueAction,
    DialogueInput,
    DialogueOutput,
    ExtractionResult,
    FinalCallOutput,
    HandoffReason,
    RoutingStatus,
    SessionState,
    VehicleMatchStatus,
)
from .post_call import PostCallBuilder
from .response_generator import ResponseGenerator
from .schemas import get_category_schema
from .state_updater import StateUpdater
from .turn_analyzer import LLMTurnAnalyzer, TurnAnalysisError, TurnAnalysisResult
from .validators import FieldValidator
from .vehicle_matcher import VehicleMatcher


class DialogueOrchestrator:
    """Coordinate one dialogue turn from DialogueInput to DialogueOutput."""

    _MODEL_AFTER_XE_RE = re.compile(r"\bxe\s+([A-Za-z0-9À-ỹĐđ\s.-]{2,40})", re.IGNORECASE)
    _MODEL_STOP_WORDS = {
        "toi",
        "minh",
        "cua",
        "duoc",
        "dang",
        "nay",
        "bi",
        "bao",
        "can",
        "muon",
        "khong",
        "het",
        "chet",
        "loi",
        "o",
        "tai",
        "so",
        "bien",
        "vin",
        "dung",
    }

    def __init__(
        self,
        router: Any | None = None,
        signal_extractor: Any | None = None,
        correction_detector: Any | None = None,
        emergency_detector: Any | None = None,
        field_extractor: Any | None = None,
        state_updater: StateUpdater | None = None,
        exception_handler: Any | None = None,
        action_policy: DialogueActionPolicy | None = None,
        response_generator: ResponseGenerator | None = None,
        vehicle_matcher: VehicleMatcher | None = None,
        post_call_builder: PostCallBuilder | None = None,
        turn_analyzer: LLMTurnAnalyzer | None = None,
        field_validator: FieldValidator | None = None,
    ) -> None:
        self.emergency_detector = emergency_detector
        self.signal_extractor = signal_extractor
        self.router = router
        self.correction_detector = correction_detector
        self.field_extractor = field_extractor
        self.state_updater = state_updater if state_updater is not None else StateUpdater()
        self.exception_handler = exception_handler
        self.action_policy = action_policy if action_policy is not None else DialogueActionPolicy()
        self.response_generator = response_generator if response_generator is not None else ResponseGenerator()
        self.vehicle_matcher = vehicle_matcher if vehicle_matcher is not None else VehicleMatcher()
        self.post_call_builder = post_call_builder if post_call_builder is not None else PostCallBuilder()
        self.turn_analyzer = turn_analyzer if turn_analyzer is not None else LLMTurnAnalyzer()
        self.field_validator = field_validator if field_validator is not None else FieldValidator()
        self._states: dict[str, SessionState] = {}
        self.last_turn_log: dict[str, Any] = {}

    def handle(self, dialogue_input: DialogueInput) -> DialogueOutput:
        """Process one transcript turn and return a validated DialogueOutput."""
        state = self._load_state(dialogue_input)
        transcript = dialogue_input.transcript or ""
        event_type = dialogue_input.metadata.get("event_type")

        if dialogue_input.metadata.get("is_final_transcript") is False:
            return self._build_output(
                state=state,
                action=ActionDecision(action=REPEAT_OR_REPHRASE, reason="partial_transcript"),
                response_text="",
                persist=False,
            )

        try:
            output = self._handle_final_turn(dialogue_input, state, transcript, event_type)
        except Exception:
            self.last_turn_log = {
                "turn_analyzer_backend": "llm",
                "llm_called": self.last_turn_log.get("llm_called", False),
                "llm_parse_success": self.last_turn_log.get("llm_parse_success", False),
                "rule_fallback_used": False,
                "error_code": "INTERNAL_DIALOGUE_ERROR",
            }
            fallback = ActionDecision(action=REPEAT_OR_REPHRASE, reason="internal_dialogue_error")
            output = self._build_output(
                state=state,
                action=fallback,
                response_text=self.response_generator.generate(fallback, state).response_text,
                persist=True,
            )
        return output

    def get_state(self, session_id: str) -> SessionState | None:
        """Return stored state for tests or host integration."""
        return self._states.get(session_id)

    def build_final_call_output(self, session_id: str, *, partial: bool = False) -> FinalCallOutput | None:
        """Build final or partial JSON for a stored categorized session."""
        state = self.get_state(session_id)
        if state is None:
            return None
        return self.post_call_builder.build(state, partial=partial)

    def _handle_final_turn(
        self,
        dialogue_input: DialogueInput,
        state: SessionState,
        transcript: str,
        event_type: str | None,
    ) -> DialogueOutput:
        metadata = dict(dialogue_input.metadata)
        if self._is_hangup(event_type, metadata):
            state = self._state_with_updates(state, {"status": CallStatus.PARTIAL.value})
            action = ActionDecision(action=END_PARTIAL_CALL, reason="hangup")
            response = self.response_generator.generate(action, state).response_text
            return self._build_output(state, action, response, persist=True, dialogue_input=dialogue_input)

        try:
            analysis = self.turn_analyzer.analyze(dialogue_input, state)
        except TurnAnalysisError as exc:
            return self._output_from_analyzer_error(state, dialogue_input, str(exc))

        self.last_turn_log = dict(analysis.log)
        state = self._state_from_analysis_metadata(state, analysis)
        if not analysis.understood:
            return self._output_low_understanding(state, dialogue_input)

        if analysis.out_of_scope:
            state = self._state_with_updates(
                state,
                {
                    "transfer_to_human": True,
                    "handoff_reason": HandoffReason.OUT_OF_SCOPE.value,
                    "routing_status": RoutingStatus.UNRESOLVED.value,
                },
            )
            action = ActionDecision(action=TRANSFER_TO_HUMAN, reason="out_of_scope")
            response = self.response_generator.generate(action, state).response_text
            return self._build_output(state, action, response, persist=True, dialogue_input=dialogue_input)

        if self._needs_intent_clarification(state, analysis):
            state = self._apply_analysis_clarification(state, analysis)
            action = ActionDecision(
                action="ASK_INTENT_CLARIFICATION",
                target_field=state.pending_field,
                reason="llm_routing_needs_clarification",
            )
            response = self.response_generator.generate(action, state).response_text
            return self._build_output(state, action, response, persist=True, dialogue_input=dialogue_input)

        category = self._target_category(state, analysis)
        extraction = ExtractionResult()
        correction = CorrectionDetectionResult(False)
        if category is not None:
            extraction, correction = self._validated_results_from_analysis(category, analysis)

        state = self.state_updater.update(
            state,
            category=category,
            extraction_result=extraction,
            correction_result=correction if correction.is_correction else None,
        )
        state = self._state_from_analysis_metadata(state, analysis)
        self._ensure_g5_troubleshooting(state)

        action = self.action_policy.decide(
            state,
            correction_result=correction if correction.is_correction else None,
            event_type=event_type,
            metadata=metadata,
        )
        if action.action == "HANDLE_EMERGENCY" and action.target_field:
            state = self._state_with_updates(state, {"pending_field": action.target_field})
            response = self._emergency_follow_up_response(action.target_field)
        else:
            response = self.response_generator.generate(action, state).response_text
        return self._build_output(state, action, response, persist=True, dialogue_input=dialogue_input)

    def _load_state(self, dialogue_input: DialogueInput) -> SessionState:
        if dialogue_input.state:
            return self._state_from_dict(dialogue_input.state)
        existing = self._states.get(dialogue_input.session_id)
        if existing is not None:
            return existing
        return SessionState(session_id=dialogue_input.session_id, turn_id=dialogue_input.turn_id)

    @staticmethod
    def _state_from_dict(data: dict[str, Any]) -> SessionState:
        payload = dict(data)
        payload.setdefault("session_id", "input-state")
        return SessionState(**payload)

    @staticmethod
    def _is_hangup(event_type: str | None, metadata: dict[str, Any]) -> bool:
        return event_type == "hangup" or metadata.get("event_type") == "hangup"

    def _output_from_analyzer_error(
        self,
        state: SessionState,
        dialogue_input: DialogueInput,
        error: str,
    ) -> DialogueOutput:
        failed_turn_count = state.failed_turn_count + 1
        updates: dict[str, Any] = {"failed_turn_count": failed_turn_count}
        if failed_turn_count >= 2:
            updates.update(
                {
                    "transfer_to_human": True,
                    "handoff_reason": HandoffReason.FAILED_UNDERSTANDING.value,
                }
            )
            action = ActionDecision(action=TRANSFER_TO_HUMAN, reason="llm_analysis_failed_twice")
        else:
            action = ActionDecision(action=REPEAT_OR_REPHRASE, reason="llm_analysis_failed")

        self.last_turn_log = {
            "turn_analyzer_backend": "llm",
            "llm_called": True,
            "llm_parse_success": False,
            "rule_fallback_used": False,
            "error_code": "LLM_OUTPUT_INVALID",
            "error": error,
        }
        state = self._state_with_updates(state, updates)
        response = self.response_generator.generate(action, state).response_text
        return self._build_output(state, action, response, persist=True, dialogue_input=dialogue_input)

    def _state_from_analysis_metadata(self, state: SessionState, analysis: TurnAnalysisResult) -> SessionState:
        updates: dict[str, Any] = {"service_goal": analysis.user_goal}
        if analysis.emergency.is_emergency:
            updates.update(
                {
                    "emergency": True,
                    "emergency_reason": analysis.emergency.reason,
                    "transfer_to_human": analysis.emergency.requires_immediate_handoff,
                    "handoff_reason": HandoffReason.EMERGENCY.value
                    if analysis.emergency.requires_immediate_handoff
                    else state.handoff_reason,
                }
            )
        return self._state_with_updates(state, updates)

    def _output_low_understanding(
        self,
        state: SessionState,
        dialogue_input: DialogueInput,
    ) -> DialogueOutput:
        failed_turn_count = state.failed_turn_count + 1
        state = self._state_with_updates(state, {"failed_turn_count": failed_turn_count})
        action_name = TRANSFER_TO_HUMAN if failed_turn_count >= 2 else REPEAT_OR_REPHRASE
        if action_name == TRANSFER_TO_HUMAN:
            state = self._state_with_updates(
                state,
                {
                    "transfer_to_human": True,
                    "handoff_reason": HandoffReason.FAILED_UNDERSTANDING.value,
                },
            )
        action = ActionDecision(action=action_name, reason="llm_did_not_understand")
        response = self.response_generator.generate(action, state).response_text
        return self._build_output(state, action, response, persist=True, dialogue_input=dialogue_input)

    def _needs_intent_clarification(self, state: SessionState, analysis: TurnAnalysisResult) -> bool:
        if analysis.emergency.is_emergency or self._category_confirmed(state):
            return False
        return analysis.category is None and analysis.routing_status == RoutingStatus.NEEDS_CLARIFICATION

    def _apply_analysis_clarification(self, state: SessionState, analysis: TurnAnalysisResult) -> SessionState:
        data = state.to_dict()
        data["category"] = None
        data["routing_status"] = RoutingStatus.NEEDS_CLARIFICATION.value
        data["candidate_categories"] = [category.value for category in analysis.candidate_categories]
        data["pending_field"] = analysis.pending_field or (analysis.ambiguities[0] if analysis.ambiguities else None)
        data["status"] = CallStatus.ROUTING.value
        data["clarification_count"] = data.get("clarification_count", 0) + 1
        return SessionState(**data)

    def _target_category(self, state: SessionState, analysis: TurnAnalysisResult) -> Category | None:
        if analysis.emergency.is_emergency:
            return analysis.category or Category.G_1
        if analysis.category is not None:
            return analysis.category
        if self._category_confirmed(state):
            return Category(state.category) if state.category is not None else None
        return None

    def _validated_results_from_analysis(
        self,
        category: Category,
        analysis: TurnAnalysisResult,
    ) -> tuple[ExtractionResult, CorrectionDetectionResult]:
        fields = dict(analysis.fields)
        uncertain_fields = dict(analysis.uncertain_fields)
        fields, uncertain_fields = self._normalize_vehicle_fields(category, fields, uncertain_fields)
        valid_fields, validation_uncertain, errors = self.field_validator.validate_fields(category, fields)
        uncertain_fields.update(validation_uncertain)
        extraction = ExtractionResult(
            fields=valid_fields,
            uncertain_fields=self._allowed_fields(category, uncertain_fields),
            internal_signals={
                "turn_analyzer_backend": "llm",
                "validation_errors": errors,
                "ambiguities": list(analysis.ambiguities),
            },
            corrections=[],
        )

        correction_fields = {
            str(item["field"]): item.get("value")
            for item in analysis.corrections
            if item.get("field") is not None
        }
        correction_fields, _ = self._normalize_vehicle_fields(category, correction_fields, {})
        valid_corrections, _, _ = self.field_validator.validate_fields(category, correction_fields)
        correction = CorrectionDetectionResult(
            is_correction=bool(valid_corrections),
            corrected_fields=valid_corrections,
            field_confidences={
                str(item["field"]): float(item.get("confidence", 0.99))
                for item in analysis.corrections
                if item.get("field") in valid_corrections
            },
            evidence=[
                str(item.get("reason") or "llm_detected_correction")
                for item in analysis.corrections
                if item.get("field") in valid_corrections
            ],
        )
        return extraction, correction

    def _normalize_vehicle_fields(
        self,
        category: Category,
        fields: dict[str, Any],
        uncertain_fields: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        result = dict(fields)
        uncertain = dict(uncertain_fields)
        target_field = "vehicle_line" if category in {Category.G_4, Category.G_5} else "vehicle_model"
        raw_value = result.get(target_field)
        if raw_value is None:
            return result, uncertain

        match = self.vehicle_matcher.match(str(raw_value))
        status = match.status.value if hasattr(match.status, "value") else str(match.status)
        vehicle_type = match.vehicle_type.value if hasattr(match.vehicle_type, "value") else str(match.vehicle_type)
        if status != VehicleMatchStatus.CONFIRMED.value or not match.canonical_name:
            result.pop(target_field, None)
            uncertain[target_field] = raw_value
            return result, uncertain

        if category == Category.G_2 and vehicle_type != "car":
            result.pop(target_field, None)
            uncertain[target_field] = raw_value
            return result, uncertain
        if category == Category.G_4 and vehicle_type != "motorbike":
            result.pop(target_field, None)
            uncertain[target_field] = raw_value
            return result, uncertain

        result[target_field] = match.canonical_name
        if category == Category.G_1 and vehicle_type in {"car", "motorbike"}:
            result["vehicle_type"] = vehicle_type
        return result, uncertain

    @staticmethod
    def _allowed_fields(category: Category, fields: dict[str, Any]) -> dict[str, Any]:
        allowed = set(get_category_schema(category).all_fields)
        return {field_name: value for field_name, value in fields.items() if field_name in allowed}

    @staticmethod
    def _state_with_updates(state: SessionState, updates: dict[str, Any]) -> SessionState:
        data = state.to_dict()
        for key, value in updates.items():
            if key in data:
                data[key] = value
        return SessionState(**data)

    @staticmethod
    def _emergency_follow_up_response(target_field: str) -> str:
        safety = "Dạ anh/chị hãy ưu tiên an toàn, di chuyển tới nơi an toàn nếu có thể."
        questions = {
            "current_location": "Anh/chị cho em xin vị trí hiện tại để chuyển hỗ trợ ngay ạ?",
            "city_name": "Anh/chị đang ở tỉnh hoặc thành phố nào ạ?",
            "phone": "Anh/chị cho em xin số điện thoại liên hệ ạ?",
            "full_name": "Anh/chị cho em xin họ tên ạ?",
            "vehicle_condition": "Anh/chị cho em biết ngắn tình trạng người và xe hiện tại ạ?",
            "vehicle_model": "Anh/chị cho em xin dòng xe ạ?",
            "license_plate_vin": "Anh/chị cho em xin biển số hoặc số VIN của xe ạ?",
            "vehicle_type": "Anh/chị đang sử dụng ô tô hay xe máy điện ạ?",
            "current_odo": "Anh/chị cho em xin số kilomet hiện tại của xe ạ?",
        }
        question = questions.get(target_field)
        if question:
            return f"{safety} {question}"
        return f"{safety} Em sẽ chuyển tư vấn viên hỗ trợ ngay ạ."

    def _vehicle_match_from_transcript(self, transcript: str) -> VehicleMatchResult | None:
        known = self.signal_extractor._match_vehicle_in_text(transcript)
        if known is not None:
            return known

        match = self._MODEL_AFTER_XE_RE.search(transcript)
        if match is None:
            return None
        words = match.group(1).strip(" ,.;").split()
        if not words:
            return None
        first_word = normalize_vehicle_text(words[0])
        if first_word in self._MODEL_STOP_WORDS:
            return None
        model_words: list[str] = []
        for word in words:
            normalized = normalize_vehicle_text(word)
            if normalized in self._MODEL_STOP_WORDS:
                break
            model_words.append(word.strip(" ,.;"))
            if len(model_words) >= 4:
                break
        raw_model = " ".join(model_words).strip()
        if not raw_model:
            return None
        return self.vehicle_matcher.match(raw_model)

    @staticmethod
    def _category_confirmed(state: SessionState) -> bool:
        status = state.routing_status.value if hasattr(state.routing_status, "value") else state.routing_status
        return state.category is not None and status == RoutingStatus.CONFIRMED.value

    def _apply_routing_clarification(self, state: SessionState, routing: Any) -> SessionState:
        data = state.to_dict()
        data["category"] = None
        data["routing_status"] = RoutingStatus.NEEDS_CLARIFICATION.value
        data["candidate_categories"] = [self._value(category) for category in routing.candidate_categories]
        data["pending_field"] = routing.missing_discriminator
        data["status"] = CallStatus.ROUTING.value
        data["clarification_count"] = data.get("clarification_count", 0) + 1
        return SessionState(**data)

    def _apply_exception_updates(self, state: SessionState, exception: ExceptionResult) -> SessionState:
        data = state.to_dict()
        updates = dict(exception.state_updates)
        failed_delta = int(updates.pop("failed_turn_count_delta", 0) or 0)
        if failed_delta:
            data["failed_turn_count"] = data.get("failed_turn_count", 0) + failed_delta
        for key, value in updates.items():
            if key in data:
                data[key] = value
        return SessionState(**data)

    def _output_from_exception(
        self,
        state: SessionState,
        exception: ExceptionResult,
        dialogue_input: DialogueInput,
    ) -> DialogueOutput:
        action = ActionDecision(
            action=exception.action or REPEAT_OR_REPHRASE,
            target_field=exception.target_field,
            reason=exception.reason_code or "exception",
            metadata=dict(exception.metadata),
        )
        response = self.response_generator.generate(action, state).response_text
        return self._build_output(state, action, response, persist=True, dialogue_input=dialogue_input)

    def _ensure_g5_troubleshooting(self, state: SessionState) -> None:
        category = self._value(state.category)
        if category != Category.G_5.value:
            return
        schema = get_category_schema(Category.G_5)
        has_required = all(field in state.confirmed_fields for field in schema.required_fields)
        if has_required and "troubleshooting" not in state.fields:
            state.fields["troubleshooting"] = {"steps_attempted": [], "resolved": False}

    def _build_output(
        self,
        state: SessionState,
        action: ActionDecision,
        response_text: str,
        persist: bool,
        dialogue_input: DialogueInput | None = None,
    ) -> DialogueOutput:
        next_action = self._contract_action(action.action)
        if dialogue_input is not None:
            state = self._append_history(state, dialogue_input.transcript, response_text, next_action.value)
        if persist:
            self._states[state.session_id] = state

        output = DialogueOutput(
            response_text=response_text,
            category=state.category,
            routing_status=state.routing_status,
            candidate_categories=state.candidate_categories,
            fields=self._public_fields(state),
            confirmed_fields=state.confirmed_fields,
            unconfirmed_fields=state.unconfirmed_fields,
            missing_fields=state.missing_fields,
            pending_field=state.pending_field,
            next_action=next_action,
            status=self._output_status(state, next_action),
            failed_turn_count=state.failed_turn_count,
            transfer_to_human=state.transfer_to_human or next_action == DialogueAction.TRANSFER_TO_HUMAN,
            handoff_reason=state.handoff_reason,
            emergency=state.emergency,
            should_end_call=next_action == DialogueAction.END_PARTIAL_CALL,
        )
        return output

    def _append_history(
        self,
        state: SessionState,
        transcript: str,
        response_text: str,
        last_action: str,
    ) -> SessionState:
        data = state.to_dict()
        history = list(data["conversation_history"])
        if transcript:
            history.append({"role": "user", "content": transcript})
        history.append({"role": "assistant", "content": response_text})
        data["conversation_history"] = history
        data["turn_id"] = data.get("turn_id", 0) + 1
        data["last_action"] = last_action
        return SessionState(**data)

    @staticmethod
    def _contract_action(action: str) -> DialogueAction:
        if action == CONFIRM_VEHICLE_MODEL:
            return DialogueAction.CONFIRM_UNCLEAR_FIELD
        try:
            return DialogueAction(action)
        except ValueError:
            return DialogueAction.REPEAT_OR_REPHRASE

    def _output_status(self, state: SessionState, action: DialogueAction) -> CallStatus:
        if action == DialogueAction.END_PARTIAL_CALL:
            return CallStatus.PARTIAL
        if action == DialogueAction.TRANSFER_TO_HUMAN or state.transfer_to_human:
            return CallStatus.TRANSFERRED
        if action == DialogueAction.CONFIRM_COLLECTED_INFORMATION:
            return CallStatus.CONFIRMING
        if action == DialogueAction.FINALIZE_CALL:
            return CallStatus.COMPLETED
        if action in {DialogueAction.PROVIDE_REMOTE_STEP, DialogueAction.ASK_REMOTE_STEP_RESULT}:
            return CallStatus.TROUBLESHOOTING
        if not self._category_confirmed(state):
            return CallStatus.ROUTING
        return CallStatus.COLLECTING

    def _public_fields(self, state: SessionState) -> dict[str, Any]:
        if state.category is None:
            return dict(state.fields)
        schema = get_category_schema(state.category)
        return schema.build_final_fields(state.fields)

    @staticmethod
    def _value(value: Any) -> Any:
        if isinstance(value, Enum):
            return value.value
        return value
