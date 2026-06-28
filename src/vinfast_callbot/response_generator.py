"""Deterministic Vietnamese response generation.

The generator renders a response for an already selected dialogue action. It
does not choose or change the action, and it does not mutate SessionState.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass, field
from typing import Any, Callable

from .action_policy import (
    ACKNOWLEDGE_CORRECTION,
    ASK_INTENT_CLARIFICATION,
    ASK_MISSING_FIELD,
    ASK_REMOTE_STEP_RESULT,
    CONFIRM_COLLECTED_INFORMATION,
    CONFIRM_UNCLEAR_FIELD,
    CONFIRM_VEHICLE_MODEL,
    END_PARTIAL_CALL,
    FINALIZE_CALL,
    HANDLE_EMERGENCY,
    PROVIDE_REMOTE_STEP,
    REPEAT_OR_REPHRASE,
    TRANSFER_TO_HUMAN,
    ActionDecision,
)
from .models import Category, SessionState


LLMRenderer = Callable[[dict[str, Any]], str]


@dataclass(frozen=True, slots=True)
class GeneratedResponse:
    """Generated response text with render metadata."""

    response_text: str
    action: str
    target_field: str | None = None
    used_fallback: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "response_text": self.response_text,
            "action": self.action,
            "target_field": self.target_field,
            "used_fallback": self.used_fallback,
            "metadata": dict(self.metadata),
        }


class ResponseGenerator:
    """Render short Vietnamese responses from structured actions."""

    _FIELD_QUESTIONS = {
        "full_name": "Dạ anh/chị cho em xin họ tên ạ.",
        "phone": "Dạ anh/chị cho em xin số điện thoại liên hệ ạ.",
        "owner_phone": "Dạ anh/chị cho em xin số điện thoại của chủ xe ạ.",
        "order_phone": "Dạ anh/chị cho em xin số điện thoại dùng cho đơn hàng ạ.",
        "vehicle_model": "Dạ anh/chị cho em xin dòng xe ạ.",
        "vehicle_line": "Dạ anh/chị cho em xin dòng xe ạ.",
        "license_plate_vin": "Dạ anh/chị cho em xin biển số hoặc số VIN của xe ạ.",
        "vehicle_type": "Dạ anh/chị đang sử dụng ô tô hay xe máy điện ạ?",
        "current_odo": "Dạ anh/chị cho em xin số kilomet hiện tại của xe ạ.",
        "current_location": "Dạ anh/chị cho em xin vị trí hiện tại của xe ạ.",
        "city_name": "Dạ anh/chị đang ở tỉnh hoặc thành phố nào ạ?",
        "vehicle_condition": "Dạ anh/chị mô tả ngắn tình trạng xe hiện tại giúp em ạ.",
        "vehicle_condition_details": "Dạ anh/chị mô tả ngắn lỗi đang gặp giúp em ạ.",
        "vehicle_usage_type": "Dạ xe đang được sử dụng cho cá nhân hay kinh doanh ạ?",
        "service_center": "Dạ anh/chị muốn kiểm tra tại trung tâm dịch vụ nào ạ?",
        "order_code_dealer": "Dạ anh/chị cho em xin mã đơn hàng hoặc tên đại lý ạ.",
        "customer_type": "Dạ anh/chị là khách hàng cá nhân hay doanh nghiệp ạ?",
    }
    _FIELD_LABELS = {
        "full_name": "họ tên",
        "phone": "số điện thoại",
        "owner_phone": "số điện thoại chủ xe",
        "order_phone": "số điện thoại đơn hàng",
        "vehicle_model": "dòng xe",
        "vehicle_line": "dòng xe",
        "license_plate_vin": "biển số hoặc số VIN",
        "vehicle_type": "loại xe",
        "current_odo": "số kilomet",
        "current_location": "vị trí hiện tại",
        "city_name": "tỉnh hoặc thành phố",
        "vehicle_condition": "tình trạng xe",
        "vehicle_condition_details": "chi tiết lỗi",
        "vehicle_usage_type": "mục đích sử dụng xe",
        "service_center": "trung tâm dịch vụ",
        "order_code_dealer": "mã đơn hoặc đại lý",
        "customer_type": "loại khách hàng",
    }

    def __init__(
        self,
        llm_renderer: LLMRenderer | None = None,
        use_llm: bool = False,
        llm_timeout_seconds: float = 1.5,
    ) -> None:
        self.llm_renderer = llm_renderer
        self.use_llm = use_llm
        self.llm_timeout_seconds = llm_timeout_seconds

    def generate(
        self,
        action: str | ActionDecision,
        state: SessionState,
        target_field: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> GeneratedResponse:
        """Render response text for the provided action without changing state."""
        action_name, resolved_target, action_metadata = self._resolve_action(action, target_field, metadata)
        fallback_text = self._deterministic_response(action_name, state, resolved_target, action_metadata)

        if not self.use_llm or self.llm_renderer is None:
            return GeneratedResponse(
                response_text=fallback_text,
                action=action_name,
                target_field=resolved_target,
                used_fallback=True,
            )

        llm_text = self._try_llm(action_name, state, resolved_target, action_metadata)
        if llm_text is None:
            return GeneratedResponse(
                response_text=fallback_text,
                action=action_name,
                target_field=resolved_target,
                used_fallback=True,
                metadata={"fallback_reason": "llm_failed"},
            )
        return GeneratedResponse(
            response_text=llm_text,
            action=action_name,
            target_field=resolved_target,
            used_fallback=False,
        )

    @staticmethod
    def _resolve_action(
        action: str | ActionDecision,
        target_field: str | None,
        metadata: dict[str, Any] | None,
    ) -> tuple[str, str | None, dict[str, Any]]:
        if isinstance(action, ActionDecision):
            merged_metadata = dict(action.metadata)
            if metadata:
                merged_metadata.update(metadata)
            return action.action, target_field or action.target_field, merged_metadata
        return action, target_field, dict(metadata or {})

    def _deterministic_response(
        self,
        action: str,
        state: SessionState,
        target_field: str | None,
        metadata: dict[str, Any],
    ) -> str:
        if action == ASK_INTENT_CLARIFICATION:
            return self._intent_clarification(target_field)
        if action == ASK_MISSING_FIELD:
            return self._missing_field_question(target_field, state)
        if action == CONFIRM_UNCLEAR_FIELD:
            return self._confirm_unclear_field(target_field)
        if action == CONFIRM_VEHICLE_MODEL:
            return self._confirm_vehicle_model(target_field, metadata)
        if action == ACKNOWLEDGE_CORRECTION:
            return self._correction_ack(metadata)
        if action == HANDLE_EMERGENCY:
            return self._emergency_response(metadata)
        if action == TRANSFER_TO_HUMAN:
            return "Dạ em sẽ chuyển anh/chị đến tư vấn viên để được hỗ trợ chính xác hơn ạ."
        if action == CONFIRM_COLLECTED_INFORMATION:
            return self._final_confirmation(state)
        if action == FINALIZE_CALL:
            return "Dạ em đã ghi nhận thông tin. Cảm ơn anh/chị ạ."
        if action == END_PARTIAL_CALL:
            return "Dạ em ghi nhận cuộc gọi kết thúc tại đây và sẽ lưu thông tin hiện có ạ."
        if action == REPEAT_OR_REPHRASE:
            return "Dạ em chưa nghe rõ, anh/chị vui lòng nói lại giúp em ạ."
        if action == PROVIDE_REMOTE_STEP:
            return "Dạ anh/chị thử khởi động lại hệ thống màn hình và cho em biết kết quả ạ."
        if action == ASK_REMOTE_STEP_RESULT:
            return "Dạ sau bước vừa rồi tình trạng đã được khắc phục chưa ạ?"
        return "Dạ anh/chị vui lòng cho em thêm thông tin để hỗ trợ tiếp ạ."

    @staticmethod
    def _intent_clarification(target_field: str | None) -> str:
        if target_field == "rescue_needed":
            return "Dạ anh/chị có cần hỗ trợ cứu hộ ngay không ạ?"
        if target_field == "vehicle_type":
            return "Dạ anh/chị đang sử dụng ô tô hay xe máy điện ạ?"
        if target_field == "remote_support_preference":
            return "Dạ anh/chị muốn em hướng dẫn kiểm tra trước không ạ?"
        return "Dạ anh/chị cần hỗ trợ vấn đề gì với xe ạ?"

    def _missing_field_question(self, target_field: str | None, state: SessionState) -> str:
        if target_field and self._is_confirmed(state, target_field):
            next_field = self._next_unconfirmed_missing_field(state)
            if next_field is not None:
                target_field = next_field
        return self._FIELD_QUESTIONS.get(
            target_field or "",
            "Dạ anh/chị cho em xin thêm thông tin còn thiếu ạ.",
        )

    def _confirm_unclear_field(self, target_field: str | None) -> str:
        if target_field in {"phone", "owner_phone", "order_phone"}:
            return "Dạ em chưa nghe rõ số điện thoại, anh/chị vui lòng đọc lại từng số giúp em ạ."
        if target_field == "license_plate_vin":
            return "Dạ em chưa nghe rõ biển số hoặc số VIN, anh/chị vui lòng đọc lại giúp em ạ."
        if target_field == "current_odo":
            return "Dạ em chưa nghe rõ số kilomet hiện tại, anh/chị vui lòng đọc lại giúp em ạ."
        label = self._FIELD_LABELS.get(target_field or "", "thông tin này")
        return f"Dạ em chưa nghe rõ {label}, anh/chị vui lòng nói lại giúp em ạ."

    def _confirm_vehicle_model(self, target_field: str | None, metadata: dict[str, Any]) -> str:
        del target_field
        vehicle_state = metadata.get("vehicle_model_state")
        raw_text = metadata.get("raw_text")
        candidates: list[str] = []
        if isinstance(vehicle_state, dict):
            raw_text = raw_text or vehicle_state.get("raw_text") or vehicle_state.get("canonical_name")
            raw_candidates = vehicle_state.get("candidates", [])
            if isinstance(raw_candidates, list):
                candidates = [str(value) for value in raw_candidates]
        raw_candidates = metadata.get("candidates", [])
        if isinstance(raw_candidates, list):
            candidates = [str(value) for value in raw_candidates]

        if len(candidates) == 1:
            return f"Dạ anh/chị đang sử dụng dòng xe {candidates[0]} đúng không ạ?"
        if len(candidates) == 2:
            return f"Dạ anh/chị đang dùng {candidates[0]} hay {candidates[1]} ạ?"
        if raw_text:
            return f"Dạ em xin xác nhận dòng xe là {raw_text} đúng không ạ?"
        return "Dạ anh/chị vui lòng xác nhận lại dòng xe giúp em ạ."

    def _correction_ack(self, metadata: dict[str, Any]) -> str:
        corrected = metadata.get("corrected_fields", [])
        if isinstance(corrected, str):
            corrected = [corrected]
        if isinstance(corrected, list) and len(corrected) == 1:
            label = self._FIELD_LABELS.get(str(corrected[0]), "thông tin")
            return f"Dạ em đã cập nhật {label} ạ."
        return "Dạ em đã cập nhật thông tin ạ."

    @staticmethod
    def _emergency_response(metadata: dict[str, Any]) -> str:
        hotline = metadata.get("emergency_hotline")
        if hotline:
            return (
                f"Dạ anh/chị hãy ưu tiên an toàn và gọi {hotline} nếu cần hỗ trợ khẩn cấp; "
                "em sẽ chuyển tư vấn viên hỗ trợ ngay ạ."
            )
        return (
            "Dạ anh/chị hãy ưu tiên an toàn, di chuyển tới nơi an toàn nếu có thể; "
            "em sẽ chuyển tư vấn viên hỗ trợ ngay ạ."
        )

    def _final_confirmation(self, state: SessionState) -> str:
        parts = self._summary_parts(state)
        if parts:
            return f"Dạ em xin xác nhận {'; '.join(parts)}. Thông tin này đúng không ạ?"
        return "Dạ em xin xác nhận các thông tin đã ghi nhận. Thông tin này đúng không ạ?"

    def _summary_parts(self, state: SessionState) -> list[str]:
        category = state.category.value if hasattr(state.category, "value") else state.category
        fields = state.fields
        parts: list[str] = []
        name = fields.get("full_name")
        if name:
            parts.append(f"khách hàng {name}")

        model = fields.get("vehicle_model") or fields.get("vehicle_line")
        if model:
            parts.append(f"dòng xe {model}")

        if category == Category.G_3.value and fields.get("order_code_dealer"):
            parts.append(f"mã đơn hoặc đại lý {fields['order_code_dealer']}")

        condition = fields.get("vehicle_condition") or fields.get("vehicle_condition_details")
        if condition:
            parts.append(f"tình trạng {condition}")

        location = fields.get("current_location")
        if location:
            parts.append(f"vị trí {location}")
        return parts[:4]

    @staticmethod
    def _is_confirmed(state: SessionState, field_name: str) -> bool:
        return field_name in state.confirmed_fields

    @staticmethod
    def _next_unconfirmed_missing_field(state: SessionState) -> str | None:
        for field_name in state.missing_fields:
            if field_name not in state.confirmed_fields:
                return field_name
        return None

    def _try_llm(
        self,
        action: str,
        state: SessionState,
        target_field: str | None,
        metadata: dict[str, Any],
    ) -> str | None:
        if self.llm_renderer is None:
            return None
        payload = {
            "task": "render_short_vietnamese_response",
            "action": action,
            "target_field": target_field,
            "category": state.category.value if hasattr(state.category, "value") else state.category,
            "metadata": dict(metadata),
            "rules": [
                "Do not change action.",
                "Do not update state.",
                "Ask at most one question.",
                "Do not list five categories.",
                "Do not expose technical field names.",
            ],
        }
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(self.llm_renderer, payload)
        try:
            text = future.result(timeout=self.llm_timeout_seconds)
        except (TimeoutError, Exception):
            executor.shutdown(wait=False, cancel_futures=True)
            return None
        executor.shutdown(wait=False, cancel_futures=True)
        return self._validate_llm_text(text)

    @staticmethod
    def _validate_llm_text(text: str) -> str | None:
        cleaned = " ".join(str(text).strip().split())
        if not cleaned:
            return None
        if len(cleaned) > 260:
            return None
        if "G_1" in cleaned or "G_2" in cleaned or "G_3" in cleaned or "G_4" in cleaned or "G_5" in cleaned:
            return None
        if cleaned.count("?") + cleaned.count("ạ?") > 1:
            return None
        return cleaned
