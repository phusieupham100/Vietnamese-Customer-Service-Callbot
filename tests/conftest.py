"""Pytest fixtures for LLM-first dialogue tests.

Production code defaults to LocalLLMClient. Tests replace only that boundary so
unit tests stay offline while still exercising the LLM Turn Analyzer contract.
"""

from __future__ import annotations

import json
import re
from typing import Any

import pytest

from vinfast_callbot.vehicle_normalizer import normalize_vehicle_text


class SemanticFixtureLLMClient:
    """Small deterministic test double that emits TurnAnalysisResult JSON."""

    def chat(self, messages: list[dict[str, str]]) -> str:
        payload = json.loads(messages[1]["content"])
        transcript = str(payload.get("latest_transcript") or "")
        state = payload.get("current_state") if isinstance(payload.get("current_state"), dict) else {}
        return json.dumps(_analysis(transcript, state), ensure_ascii=False)


@pytest.fixture(autouse=True)
def _patch_default_local_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    import vinfast_callbot.turn_analyzer as turn_analyzer

    monkeypatch.setattr(turn_analyzer, "OpenAIAPIClient", SemanticFixtureLLMClient)


def _base() -> dict[str, Any]:
    return {
        "understood": True,
        "user_goal": "unknown",
        "category": None,
        "routing_status": "unresolved",
        "candidate_categories": [],
        "pending_field": None,
        "emergency": {
            "is_emergency": False,
            "severity": "none",
            "reason": None,
            "requires_immediate_handoff": False,
        },
        "fields": {},
        "uncertain_fields": {},
        "corrections": [],
        "ambiguities": [],
        "intent_switch": False,
        "out_of_scope": False,
        "handoff_reason": None,
    }


def _analysis(transcript: str, state: dict[str, Any]) -> dict[str, Any]:
    text = normalize_vehicle_text(transcript)
    pending = state.get("pending_field")
    category = state.get("category")
    result = _base()

    if not transcript.strip():
        result["understood"] = False
        return result

    if _is_emergency(text):
        result.update(
            {
                "user_goal": "request_emergency_rescue",
                "category": "G_1",
                "routing_status": "confirmed",
                "fields": {"vehicle_condition": transcript.strip()},
                "emergency": {
                    "is_emergency": True,
                    "severity": "high",
                    "reason": "Customer reports a serious safety risk",
                    "requires_immediate_handoff": True,
                },
            }
        )
        return result

    if pending == "rescue_needed":
        if "khong can cuu ho" in text and ("bao hanh" in text or "sua" in text or "loi" in text):
            result.update({"user_goal": "warranty_repair", "category": "G_2", "routing_status": "confirmed"})
            return result
        if text in {"co", "vang", "can", "co can"} or "can cuu ho" in text:
            result.update({"user_goal": "request_rescue", "category": "G_1", "routing_status": "confirmed"})
            return result
        if "khong" in text and ("bao hanh" in text or "sua" in text):
            result.update({"user_goal": "warranty_repair", "category": "G_2", "routing_status": "confirmed"})
            return result

    if category and pending:
        direct = _pending_field_result(str(category), str(pending), transcript)
        if direct:
            result.update({"category": category, "routing_status": "confirmed", "fields": direct})
            return result

    if "zumo" in text:
        result.update(
            {
                "understood": True,
                "category": None,
                "routing_status": "unresolved",
                "uncertain_fields": {"vehicle_model": "Zumo"},
            }
        )
        return result

    if "mua dien thoai" in text:
        result.update({"user_goal": "out_of_scope", "out_of_scope": True, "handoff_reason": "out_of_scope"})
        return result

    if "huong dan" in text or "khoi dong lai man hinh" in text:
        result.update({"user_goal": "remote_support", "category": "G_5", "routing_status": "confirmed"})
        result["fields"].update(_common_fields(transcript))
        if "vf8" in text or "xe vf8" in text:
            result["fields"]["vehicle_line"] = "VF8"
        if "treo man hinh" in text:
            result["fields"]["vehicle_condition_details"] = "xe bị treo màn hình"
        return result

    if "khong phai" in text or "sua lai" in text or "xe cua toi la" in text:
        result.update({"category": category or "G_2", "routing_status": "confirmed"})
        model = "VF9" if "vf9" in text else None
        if model:
            result["corrections"].append(
                {"field": "vehicle_model", "value": model, "confidence": 0.99, "reason": "customer corrected model"}
            )
        return result

    if "don hang" in text or "ma don" in text or "giao xe" in text or "dai ly" in text:
        result.update({"user_goal": "order_support", "category": "G_3", "routing_status": "confirmed"})
        result["fields"].update(_common_fields(transcript, phone_field="order_phone"))
        code = re.search(r"\b[A-Z]{2,}\d{2,}\b", transcript)
        if code:
            result["fields"]["order_code_dealer"] = code.group(0)
        if "ca nhan" in text:
            result["fields"]["customer_type"] = "personal"
        return result

    if "feliz" in text and ("bao hanh" in text or "can bao hanh" in text):
        result.update({"user_goal": "motorbike_warranty", "category": "G_4", "routing_status": "confirmed"})
        result["fields"].update(_common_fields(transcript))
        result["fields"]["vehicle_line"] = "Feliz"
        if "loi pin" in text:
            result["fields"]["vehicle_condition"] = "xe bị lỗi pin"
        return result

    if "bao hanh" in text or "dat lich" in text or "kiem tra" in text:
        result.update({"user_goal": "warranty_repair", "category": "G_2", "routing_status": "confirmed"})
        result["fields"].update(_common_fields(transcript, phone_field="owner_phone"))
        if "vf8" in text or "vf 8" in text:
            result["fields"]["vehicle_model"] = "VF8"
        if "green bus" in text:
            result["fields"]["vehicle_model"] = "Green Bus tám mét"
        if "loi" in text:
            result["fields"]["vehicle_condition"] = "bị lỗi"
        if "khong phai" in text or "xe cua toi la" in text:
            model = "VF9" if "vf9" in text else None
            if model:
                result["corrections"].append(
                    {"field": "vehicle_model", "value": model, "confidence": 0.99, "reason": "customer corrected model"}
                )
        return result

    if "can cuu ho" in text or "cuu ho" in text:
        result.update({"user_goal": "request_rescue", "category": "G_1", "routing_status": "confirmed"})
        result["fields"].update(_common_fields(transcript))
        if "dien thoai khong ro" in text or "so dien thoai khong ro" in text:
            result["uncertain_fields"]["phone"] = "không rõ"
        if "vf8" in text or "vf 8" in text:
            result["fields"]["vehicle_model"] = "VF8"
        if "het pin" in text:
            result["fields"]["vehicle_condition"] = "het pin"
        if "chet may" in text:
            result["fields"]["vehicle_condition"] = "chet may"
        if "oto" in text or "o to" in text:
            result["fields"]["vehicle_type"] = "car"
        return result

    if any(value in text for value in ("het pin", "chet may", "khong khoi dong", "co van de", "loi")):
        result.update(
            {
                "user_goal": "unknown",
                "category": None,
                "routing_status": "needs_clarification",
                "candidate_categories": ["G_1", "G_2", "G_5"],
                "pending_field": "rescue_needed",
                "ambiguities": ["rescue_needed"],
            }
        )
        return result

    result["understood"] = False
    return result


def _common_fields(transcript: str, phone_field: str = "phone") -> dict[str, Any]:
    fields: dict[str, Any] = {}
    name = re.search(r"(?:tôi là|toi la|tôi tên là|toi ten la)\s+([^,.;]+)", transcript, re.IGNORECASE)
    if name:
        fields["full_name"] = name.group(1).strip()
    phone = re.search(r"(?:\+?84|0)(?:[\s.\-]?\d){8,10}", transcript)
    if phone:
        fields[phone_field] = phone.group(0)
    plate = re.search(r"\b\d{2}[A-Z]\s*-?\s*\d{4,6}\b", transcript, re.IGNORECASE)
    if plate:
        fields["license_plate_vin"] = plate.group(0)
    vin = re.search(r"\b[A-HJ-NPR-Z0-9]{17}\b", transcript, re.IGNORECASE)
    if vin:
        fields["license_plate_vin"] = vin.group(0)
    odo = re.search(r"(?:odo|km)\s*(\d[\d.,]*)", transcript, re.IGNORECASE)
    if odo:
        fields["current_odo"] = odo.group(1)
    if "ha noi" in normalize_vehicle_text(transcript):
        fields["city_name"] = "Hà Nội"
    location = re.search(r"(?:ở|o|tại|tai)\s+([^,.;]+)", transcript, re.IGNORECASE)
    if location:
        fields["current_location"] = location.group(1).strip()
    return fields


def _pending_field_result(category: str, pending: str, transcript: str) -> dict[str, Any]:
    text = normalize_vehicle_text(transcript)
    if pending == "full_name":
        if text.startswith(("toi o", "minh o", "dang o", "o ", "tai ")) or text in {"ha noi", "ho chi minh"}:
            return _common_fields(transcript)
        if re.search(r"\d", transcript):
            return _common_fields(transcript)
        return {"full_name": transcript.strip()}
    if pending in {"phone", "owner_phone", "order_phone", "license_plate_vin", "current_odo"}:
        return {pending: transcript.strip()}
    if pending in {"vehicle_model", "vehicle_line"}:
        return {pending: transcript.strip()}
    if pending in {"current_location", "city_name", "vehicle_condition", "vehicle_condition_details"}:
        return {pending: transcript.strip()}
    if category == "G_1" and pending == "vehicle_type":
        return {"vehicle_type": transcript.strip()}
    return {}


def _is_emergency(text: str) -> bool:
    return any(
        phrase in text
        for phrase in (
            "dam vao cot dien",
            "lao vao mot vat",
            "choang sau cu va cham",
            "khong ra ngoai duoc",
            "tai nan",
            "bi thuong",
            "dang chay",
        )
    )
