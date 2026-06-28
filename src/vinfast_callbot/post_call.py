"""Post-call JSON builder for the Dialogue Engine.

This module builds the final JSON block described in ARCHITECTURE_NGUOI_2.md.
It does not select actions, mutate state, call ASR/TTS, or decide routing.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .models import Category, FinalCallOutput, PostCallEmergency, SessionState
from .schemas import build_final_call_output


@dataclass(frozen=True, slots=True)
class PostCallBuilder:
    """Build final or partial call JSON from a completed SessionState."""

    def build(self, state: SessionState, *, partial: bool = False) -> FinalCallOutput | None:
        """Return final JSON for categorized calls, or None before category is known."""
        category = self._value(state.category)
        if category is None:
            return None
        return build_final_call_output(
            category=category,
            collected_fields=state.fields,
            short_summary=self._short_summary(state, partial=partial),
            sentimental_analysis=self._sentiment(state),
            emergency=PostCallEmergency.YES.value if state.emergency else PostCallEmergency.NO.value,
        )

    def build_dict(self, state: SessionState, *, partial: bool = False) -> dict[str, Any] | None:
        """Return final JSON as a plain dictionary."""
        output = self.build(state, partial=partial)
        return output.to_dict() if output is not None else None

    def _short_summary(self, state: SessionState, *, partial: bool) -> str:
        category = self._value(state.category)
        fields = state.fields
        parts: list[str] = []

        name = fields.get("full_name")
        if name:
            parts.append(f"Khách hàng {name}")
        else:
            parts.append("Khách hàng")

        if category == Category.G_1.value:
            parts.append("yêu cầu hỗ trợ cứu hộ")
        elif category == Category.G_2.value:
            parts.append("cần hỗ trợ bảo hành hoặc sửa chữa ô tô")
        elif category == Category.G_3.value:
            parts.append("cần hỗ trợ đơn hàng")
        elif category == Category.G_4.value:
            parts.append("cần hỗ trợ bảo hành hoặc sửa chữa xe máy điện")
        elif category == Category.G_5.value:
            parts.append("cần hỗ trợ kỹ thuật từ xa")

        model = fields.get("vehicle_model") or fields.get("vehicle_line")
        if model:
            parts.append(f"cho xe {model}")

        condition = fields.get("vehicle_condition") or fields.get("vehicle_condition_details")
        if condition:
            parts.append(f"với tình trạng {condition}")

        location = fields.get("current_location")
        if location:
            parts.append(f"tại {location}")

        sentence = " ".join(parts).strip()
        if partial:
            sentence += " nhưng cuộc gọi kết thúc trước khi thu thập đủ thông tin"
        return sentence + "."

    @staticmethod
    def _sentiment(state: SessionState) -> str:
        if state.emergency:
            return "urgent"
        category = state.category.value if isinstance(state.category, Enum) else state.category
        if category == Category.G_1.value:
            return "urgent"
        return "calm"

    @staticmethod
    def _value(value: Any) -> Any:
        if isinstance(value, Enum):
            return value.value
        return value

