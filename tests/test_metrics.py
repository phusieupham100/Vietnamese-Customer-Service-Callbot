from evaluation.metrics import evaluate_results, normalize_value


def test_normalize_value_is_case_and_space_insensitive() -> None:
    assert normalize_value("  VF   8 ") == normalize_value("vf 8")


def test_evaluate_results_computes_core_metrics_and_failures() -> None:
    scenarios = [
        {
            "id": "ok",
            "turns": [{"expected": {"category": "G_1", "next_action": "ASK_MISSING_FIELD"}}],
            "final_expected": {"category": "G_1", "fields": {"phone": "0901234567"}},
            "tags": ["G_1"],
        },
        {
            "id": "bad",
            "turns": [{"expected": {"category": None, "next_action": "ASK_INTENT_CLARIFICATION", "tags": ["ambiguous_intent"]}}],
            "final_expected": {"category": None},
            "tags": ["ambiguous_intent"],
        },
    ]
    results = [
        {
            "id": "ok",
            "tags": ["G_1"],
            "final_expected": scenarios[0]["final_expected"],
            "final_actual": {"category": "G_1", "fields": {"phone": "0901234567"}, "status": "collecting"},
            "turns": [
                {
                    "turn_index": 0,
                    "expected": scenarios[0]["turns"][0]["expected"],
                    "actual": {"category": "G_1", "next_action": "ASK_MISSING_FIELD", "fields": {"phone": "0901234567"}},
                }
            ],
        },
        {
            "id": "bad",
            "tags": ["ambiguous_intent"],
            "final_expected": scenarios[1]["final_expected"],
            "final_actual": {"category": "G_1", "fields": {}, "status": "routing"},
            "turns": [
                {
                    "turn_index": 0,
                    "expected": scenarios[1]["turns"][0]["expected"],
                    "actual": {"category": "G_1", "next_action": "ASK_MISSING_FIELD", "fields": {}},
                }
            ],
        },
    ]

    evaluation = evaluate_results(scenarios, results)

    assert evaluation["metrics"]["routing"]["category_accuracy"] == 1.0
    assert evaluation["metrics"]["dialogue"]["next_action_accuracy"] == 0.5
    assert evaluation["metrics"]["routing"]["premature_routing_rate"] == 1.0
    assert evaluation["failure_details"]


def test_schema_compliance_metric_detects_invalid_field() -> None:
    scenarios = [
        {"id": "schema", "turns": [], "final_expected": {"category": "G_3"}, "tags": []}
    ]
    results = [
        {
            "id": "schema",
            "tags": [],
            "final_expected": {"category": "G_3"},
            "final_actual": {"category": "G_3", "fields": {"license_plate_vin": "30A-12345"}},
            "turns": [],
        }
    ]

    evaluation = evaluate_results(scenarios, results)

    assert evaluation["metrics"]["output"]["schema_compliance_rate"] == 0.0
