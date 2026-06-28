# Dialogue Engine Evaluation Report

## Objective
Evaluate routing, field extraction, dialogue behavior, vehicle model handling, exceptions, and output validity using actual DialogueOrchestrator outputs.

## Scenario Set
- Scenarios: 21
- Turns: 25

## Metrics
### routing
| Metric | Value |
|---|---:|
| `category_accuracy` | 1.000 |
| `premature_routing_rate` | 0.000 |
| `clarification_accuracy` | 1.000 |
| `routing_after_clarification_accuracy` | 1.000 |
| `emergency_false_positive_rate` | 0.000 |

### fields
| Metric | Value |
|---|---:|
| `field_exact_match` | 1.000 |
| `field_precision` | 1.000 |
| `field_recall` | 1.000 |
| `required_field_completion_rate` | 0.267 |
| `hallucinated_field_rate` | 0.000 |
| `critical_field_confirmation_rate` | 1.000 |
| `correction_update_rate` | 1.000 |

### dialogue
| Metric | Value |
|---|---:|
| `next_action_accuracy` | 1.000 |
| `dialogue_success_rate` | 1.000 |
| `no_reask_rate` | 1.000 |
| `exception_handling_success_rate` | 1.000 |
| `handoff_accuracy` | 1.000 |
| `average_turns_to_completion` | 1.000 |

### vehicle
| Metric | Value |
|---|---:|
| `vehicle_model_exact_match` | 1.000 |
| `vehicle_type_accuracy` | 1.000 |
| `vehicle_alias_resolution_rate` | 1.000 |
| `vehicle_model_confirmation_accuracy` | N/A |
| `unknown_model_false_mapping_rate` | 0.000 |

### output
| Metric | Value |
|---|---:|
| `json_validity_rate` | 1.000 |
| `schema_compliance_rate` | 1.000 |
| `partial_json_correctness` | 1.000 |
| `post_call_completeness` | N/A |

## Overall Results
- Failure records: 0

## Results By Category
- G_1: 5
- G_2: 4
- G_3: 2
- G_4: 2
- G_5: 2
- unresolved: 6

## Exception Results
- `exception_missing_field`: final action `ASK_MISSING_FIELD`
- `exception_correction_model`: final action `ACKNOWLEDGE_CORRECTION`
- `exception_ambiguous_intent`: final action `ASK_INTENT_CLARIFICATION`
- `exception_out_of_scope`: final action `TRANSFER_TO_HUMAN`
- `exception_unclear_phone`: final action `CONFIRM_UNCLEAR_FIELD`
- `exception_emergency`: final action `HANDLE_EMERGENCY`
- `exception_two_failed_turns`: final action `TRANSFER_TO_HUMAN`
- `exception_hangup_partial`: final action `END_PARTIAL_CALL`
- `exception_unknown_model`: final action `CONFIRM_UNCLEAR_FIELD`
- `no_reask_confirmed_phone`: final action `ASK_MISSING_FIELD`

## Latency Breakdown
Latency is measured per dialogue turn inside the evaluation runner.
- average_dialogue_turn_ms: 9.266
- max_dialogue_turn_ms: 17.748

## Failure Cases
- No failures recorded.

## Limitations
- Metrics are computed from the scenarios in this repository only.
- Post-call JSON completeness is reported as not applicable unless scenarios include post_call expectations.

## Improvement Plan
- Add more ASR-noise and long multi-turn scenarios.
- Add final post-call JSON evaluation once finalization is wired into the runtime.
