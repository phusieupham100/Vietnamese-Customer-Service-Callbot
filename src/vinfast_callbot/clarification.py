"""Targeted clarification helpers for unresolved intent routing."""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import DialogueAction
from .signal_extractor import InternalSignals


@dataclass(frozen=True, slots=True)
class TargetedClarification:
    """One concise clarification question and its internal routing metadata."""

    question: str
    missing_discriminator: str
    candidate_categories: list[str] = field(default_factory=list)
    next_action: DialogueAction = DialogueAction.ASK_INTENT_CLARIFICATION
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "question": self.question,
            "missing_discriminator": self.missing_discriminator,
            "candidate_categories": list(self.candidate_categories),
            "next_action": self.next_action.value,
            "evidence": list(self.evidence),
        }


def build_targeted_clarification(signals: InternalSignals) -> TargetedClarification:
    """Build one targeted clarification without listing all five categories."""
    if _needs_vehicle_type(signals):
        return TargetedClarification(
            question="Dạ anh/chị đang sử dụng ô tô hay xe máy điện ạ?",
            missing_discriminator="vehicle_type",
            candidate_categories=["G_2", "G_4"],
            evidence=["warranty_or_repair_request", "vehicle_type_unknown"],
        )

    if signals.symptom:
        if signals.can_move is False:
            return TargetedClarification(
                question="Dạ anh/chị có cần hỗ trợ cứu hộ ngay không ạ?",
                missing_discriminator="rescue_needed",
                candidate_categories=["G_1", "G_2", "G_5"],
                evidence=["symptom_only", signals.symptom],
            )
        return TargetedClarification(
            question="Dạ anh/chị muốn em hướng dẫn kiểm tra trước không ạ?",
            missing_discriminator="remote_support_preference",
            candidate_categories=["G_2", "G_5"],
            evidence=["technical_symptom_only", signals.symptom],
        )

    return TargetedClarification(
        question="Dạ anh/chị cần hỗ trợ vấn đề gì với xe ạ?",
        missing_discriminator="service_goal",
        candidate_categories=["G_1", "G_2", "G_3", "G_4", "G_5"],
        evidence=["service_goal_unknown"],
    )


def _needs_vehicle_type(signals: InternalSignals) -> bool:
    return (
        signals.vehicle_type == "unknown"
        and (signals.explicit_repair_request or signals.explicit_warranty_request)
    )
