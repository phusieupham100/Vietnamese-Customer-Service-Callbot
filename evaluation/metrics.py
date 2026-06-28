"""Automated metrics for Dialogue Engine evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from vinfast_callbot.models import Category
from vinfast_callbot.schemas import get_category_schema


CRITICAL_FIELDS = {
    "phone",
    "owner_phone",
    "order_phone",
    "license_plate_vin",
    "order_code_dealer",
    "current_odo",
}


@dataclass(slots=True)
class Counter:
    """Small ratio counter."""

    numerator: int = 0
    denominator: int = 0

    def add(self, ok: bool) -> None:
        self.denominator += 1
        if ok:
            self.numerator += 1

    def rate(self, inverse: bool = False) -> float | None:
        if self.denominator == 0:
            return None
        value = self.numerator / self.denominator
        return 1.0 - value if inverse else value


def normalize_value(value: Any) -> str:
    """Normalize values for exact field comparison."""
    if value is None:
        return ""
    return " ".join(str(value).strip().casefold().split())


def evaluate_results(
    scenarios: list[dict[str, Any]],
    scenario_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute metrics and failure details from actual scenario outputs."""
    failures: list[dict[str, Any]] = []

    counters = {
        "category_accuracy": Counter(),
        "premature_routing": Counter(),
        "clarification_accuracy": Counter(),
        "routing_after_clarification_accuracy": Counter(),
        "emergency_false_positive": Counter(),
        "field_exact_match": Counter(),
        "field_precision": Counter(),
        "field_recall": Counter(),
        "required_field_completion_rate": Counter(),
        "hallucinated_field": Counter(),
        "critical_field_confirmation_rate": Counter(),
        "correction_update_rate": Counter(),
        "next_action_accuracy": Counter(),
        "dialogue_success_rate": Counter(),
        "no_reask_rate": Counter(),
        "exception_handling_success_rate": Counter(),
        "handoff_accuracy": Counter(),
        "json_validity_rate": Counter(),
        "schema_compliance_rate": Counter(),
        "partial_json_correctness": Counter(),
        "post_call_completeness": Counter(),
        "vehicle_model_exact_match": Counter(),
        "vehicle_type_accuracy": Counter(),
        "vehicle_alias_resolution_rate": Counter(),
        "vehicle_model_confirmation_accuracy": Counter(),
        "unknown_model_false_mapping": Counter(),
    }

    turns_to_completion: list[int] = []
    scenario_by_id = {str(scenario["id"]): scenario for scenario in scenarios}

    for result in scenario_results:
        scenario = scenario_by_id[result["id"]]
        tags = set(result.get("tags", []))
        scenario_failures_before = len(failures)
        final_expected = result.get("final_expected", {})
        final_actual = result.get("final_actual", {})

        counters["dialogue_success_rate"].denominator += 1
        counters["json_validity_rate"].add(isinstance(final_actual, dict))
        counters["schema_compliance_rate"].add(_schema_compliant(final_actual))

        if final_expected.get("category") is not None:
            ok = final_actual.get("category") == final_expected.get("category")
            counters["category_accuracy"].add(ok)
            if not ok:
                _failure(failures, result, None, "category_accuracy", final_expected.get("category"), final_actual.get("category"))

        if final_expected.get("category") in {category.value for category in Category}:
            counters["required_field_completion_rate"].add(_required_fields_complete(final_actual))

        expected_final_fields = final_expected.get("fields", {})
        if expected_final_fields:
            _compare_fields(counters, failures, result, None, expected_final_fields, final_actual.get("fields", {}))

        expected_provided_fields = set(final_expected.get("provided_fields", expected_final_fields.keys()))
        actual_fields = final_actual.get("fields", {}) if isinstance(final_actual.get("fields", {}), dict) else {}
        for field_name, actual_value in actual_fields.items():
            if actual_value is None:
                continue
            if expected_provided_fields and field_name not in expected_provided_fields and not field_name.startswith("_"):
                counters["hallucinated_field"].add(True)
                _failure(failures, result, None, "hallucinated_field_rate", "no extra field", field_name)
            elif not field_name.startswith("_"):
                counters["hallucinated_field"].add(False)

        if "correction" in tags and expected_final_fields:
            counters["correction_update_rate"].add(_fields_match(expected_final_fields, actual_fields))

        if "no_reask" in tags:
            forbidden = scenario.get("no_reask_field")
            text = " ".join(turn["actual"].get("response_text", "") for turn in result.get("turns", []))
            ok = not forbidden or _field_label(forbidden) not in text.casefold()
            counters["no_reask_rate"].add(ok)
            if not ok:
                _failure(failures, result, None, "no_reask_rate", f"do not ask {forbidden}", text)

        if "routing_after_clarification" in tags and "category" in final_expected:
            counters["routing_after_clarification_accuracy"].add(final_actual.get("category") == final_expected["category"])

        if final_actual.get("status") in {"completed", "confirming"}:
            turns_to_completion.append(len(result.get("turns", [])))

        if "post_call" in final_expected:
            post_call = final_actual.get("post_call")
            counters["post_call_completeness"].add(isinstance(post_call, dict) and all(post_call.get(k) for k in final_expected["post_call"]))

        for turn in result.get("turns", []):
            _evaluate_turn(counters, failures, result, turn)

        if "exception" in tags:
            counters["exception_handling_success_rate"].add(len(failures) == scenario_failures_before)

        if len(failures) == scenario_failures_before:
            counters["dialogue_success_rate"].numerator += 1

    metrics = {
        "routing": {
            "category_accuracy": counters["category_accuracy"].rate(),
            "premature_routing_rate": counters["premature_routing"].rate(),
            "clarification_accuracy": counters["clarification_accuracy"].rate(),
            "routing_after_clarification_accuracy": counters["routing_after_clarification_accuracy"].rate(),
            "emergency_false_positive_rate": counters["emergency_false_positive"].rate(),
        },
        "fields": {
            "field_exact_match": counters["field_exact_match"].rate(),
            "field_precision": counters["field_precision"].rate(),
            "field_recall": counters["field_recall"].rate(),
            "required_field_completion_rate": counters["required_field_completion_rate"].rate(),
            "hallucinated_field_rate": counters["hallucinated_field"].rate(),
            "critical_field_confirmation_rate": counters["critical_field_confirmation_rate"].rate(),
            "correction_update_rate": counters["correction_update_rate"].rate(),
        },
        "dialogue": {
            "next_action_accuracy": counters["next_action_accuracy"].rate(),
            "dialogue_success_rate": counters["dialogue_success_rate"].rate(),
            "no_reask_rate": counters["no_reask_rate"].rate(),
            "exception_handling_success_rate": counters["exception_handling_success_rate"].rate(),
            "handoff_accuracy": counters["handoff_accuracy"].rate(),
            "average_turns_to_completion": (
                sum(turns_to_completion) / len(turns_to_completion) if turns_to_completion else None
            ),
        },
        "vehicle": {
            "vehicle_model_exact_match": counters["vehicle_model_exact_match"].rate(),
            "vehicle_type_accuracy": counters["vehicle_type_accuracy"].rate(),
            "vehicle_alias_resolution_rate": counters["vehicle_alias_resolution_rate"].rate(),
            "vehicle_model_confirmation_accuracy": counters["vehicle_model_confirmation_accuracy"].rate(),
            "unknown_model_false_mapping_rate": counters["unknown_model_false_mapping"].rate(),
        },
        "output": {
            "json_validity_rate": counters["json_validity_rate"].rate(),
            "schema_compliance_rate": counters["schema_compliance_rate"].rate(),
            "partial_json_correctness": counters["partial_json_correctness"].rate(),
            "post_call_completeness": counters["post_call_completeness"].rate(),
        },
    }
    return {"metrics": metrics, "failure_details": failures}


def _evaluate_turn(
    counters: dict[str, Counter],
    failures: list[dict[str, Any]],
    scenario_result: dict[str, Any],
    turn: dict[str, Any],
) -> None:
    expected = turn.get("expected", {})
    actual = turn.get("actual", {})

    if "next_action" in expected:
        ok = actual.get("next_action") == expected["next_action"]
        counters["next_action_accuracy"].add(ok)
        if not ok:
            _failure(failures, scenario_result, turn["turn_index"], "next_action_accuracy", expected["next_action"], actual.get("next_action"))

    if expected.get("next_action") == "ASK_INTENT_CLARIFICATION":
        counters["clarification_accuracy"].add(actual.get("next_action") == "ASK_INTENT_CLARIFICATION")

    if expected.get("category") is None and "ambiguous_intent" in expected.get("tags", []):
        ok = actual.get("category") is not None
        counters["premature_routing"].add(ok)
        if ok:
            _failure(failures, scenario_result, turn["turn_index"], "premature_routing_rate", None, actual.get("category"))

    if expected.get("emergency") is False:
        false_positive = actual.get("emergency") is True
        counters["emergency_false_positive"].add(false_positive)
        if false_positive:
            _failure(failures, scenario_result, turn["turn_index"], "emergency_false_positive_rate", False, True)

    for key in ("category", "routing_status", "pending_field", "emergency", "transfer_to_human", "handoff_reason", "status", "should_end_call"):
        if key in expected and actual.get(key) != expected[key]:
            _failure(failures, scenario_result, turn["turn_index"], key, expected[key], actual.get(key))

    if "fields" in expected:
        _compare_fields(counters, failures, scenario_result, turn["turn_index"], expected["fields"], actual.get("fields", {}))

    if "confirmed_fields_contains" in expected:
        confirmed = set(actual.get("confirmed_fields", []))
        for field_name in expected["confirmed_fields_contains"]:
            ok = field_name in confirmed
            counters["critical_field_confirmation_rate"].add(ok)
            if not ok:
                _failure(failures, scenario_result, turn["turn_index"], "critical_field_confirmation_rate", field_name, actual.get("confirmed_fields", []))

    if "unconfirmed_fields_contains" in expected:
        unconfirmed = set(actual.get("unconfirmed_fields", {}))
        for field_name in expected["unconfirmed_fields_contains"]:
            ok = field_name in unconfirmed
            counters["critical_field_confirmation_rate"].add(ok)
            if not ok:
                _failure(failures, scenario_result, turn["turn_index"], "critical_field_confirmation_rate", field_name, actual.get("unconfirmed_fields", {}))

    if expected.get("transfer_to_human") is not None or expected.get("handoff_reason") is not None:
        counters["handoff_accuracy"].add(
            actual.get("transfer_to_human") == expected.get("transfer_to_human", actual.get("transfer_to_human"))
            and actual.get("handoff_reason") == expected.get("handoff_reason", actual.get("handoff_reason"))
        )

    if expected.get("should_end_call") is True or expected.get("status") == "partial":
        counters["partial_json_correctness"].add(actual.get("should_end_call") is True and actual.get("status") == "partial")

    fields = actual.get("fields", {})
    if "vehicle_model" in expected.get("fields", {}):
        counters["vehicle_model_exact_match"].add(fields.get("vehicle_model") == expected["fields"]["vehicle_model"])
    if "vehicle_line" in expected.get("fields", {}):
        counters["vehicle_model_exact_match"].add(fields.get("vehicle_line") == expected["fields"]["vehicle_line"])
    if "vehicle_type" in expected.get("fields", {}):
        counters["vehicle_type_accuracy"].add(fields.get("vehicle_type") == expected["fields"]["vehicle_type"])
    if "vehicle_alias" in expected.get("tags", []):
        expected_model = expected.get("fields", {}).get("vehicle_model") or expected.get("fields", {}).get("vehicle_line")
        actual_model = fields.get("vehicle_model") or fields.get("vehicle_line")
        counters["vehicle_alias_resolution_rate"].add(actual_model == expected_model)
    if expected.get("next_action") == "CONFIRM_UNCLEAR_FIELD" and expected.get("pending_field") in {"vehicle_model", "vehicle_line"}:
        counters["vehicle_model_confirmation_accuracy"].add(actual.get("next_action") == "CONFIRM_UNCLEAR_FIELD")
    if "unknown_model" in expected.get("tags", []):
        mapped = bool(fields.get("vehicle_model") or fields.get("vehicle_line"))
        counters["unknown_model_false_mapping"].add(mapped)


def _compare_fields(
    counters: dict[str, Counter],
    failures: list[dict[str, Any]],
    scenario_result: dict[str, Any],
    turn_index: int | None,
    expected_fields: dict[str, Any],
    actual_fields: dict[str, Any],
) -> None:
    for field_name, expected_value in expected_fields.items():
        actual_value = actual_fields.get(field_name)
        ok = normalize_value(actual_value) == normalize_value(expected_value)
        counters["field_exact_match"].add(ok)
        counters["field_recall"].add(ok)
        if not ok:
            _failure(failures, scenario_result, turn_index, f"field_exact_match.{field_name}", expected_value, actual_value)

    for field_name, actual_value in actual_fields.items():
        if field_name.startswith("_"):
            continue
        if actual_value is None:
            continue
        if field_name in expected_fields:
            counters["field_precision"].add(normalize_value(actual_value) == normalize_value(expected_fields[field_name]))


def _fields_match(expected_fields: dict[str, Any], actual_fields: dict[str, Any]) -> bool:
    return all(normalize_value(actual_fields.get(k)) == normalize_value(v) for k, v in expected_fields.items())


def _required_fields_complete(actual: dict[str, Any]) -> bool:
    category = actual.get("category")
    if category is None:
        return False
    try:
        schema = get_category_schema(category)
    except ValueError:
        return False
    fields = actual.get("fields", {})
    return all(fields.get(field_name) is not None for field_name in schema.required_fields)


def _schema_compliant(actual: dict[str, Any]) -> bool:
    category = actual.get("category")
    if category is None:
        return True
    try:
        schema = get_category_schema(category)
    except ValueError:
        return False
    fields = actual.get("fields", {})
    return isinstance(fields, dict) and set(fields).issubset(set(schema.all_fields))


def _field_label(field_name: str) -> str:
    labels = {
        "phone": "số điện thoại",
        "owner_phone": "số điện thoại",
        "order_phone": "số điện thoại",
        "license_plate_vin": "biển số",
    }
    return labels.get(field_name, field_name).casefold()


def _failure(
    failures: list[dict[str, Any]],
    scenario_result: dict[str, Any],
    turn_index: int | None,
    metric: str,
    expected: Any,
    actual: Any,
) -> None:
    failures.append(
        {
            "scenario_id": scenario_result["id"],
            "turn_index": turn_index,
            "metric": metric,
            "expected": expected,
            "actual": actual,
        }
    )
