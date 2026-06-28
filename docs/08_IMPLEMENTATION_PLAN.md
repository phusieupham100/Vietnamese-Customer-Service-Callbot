# 08 — Implementation Plan

## 1. Mục tiêu

Triển khai theo module nhỏ để Codex không phải sửa cả hệ thống trong một task.

## 2. Thứ tự phụ thuộc

```text
Contracts
  ↓
Category Schemas
  ↓
Data Models
  ↓
Signal Extractor
  ↓
Intent Router
  ↓
Field Extractor + Validators
  ↓
State Updater
  ↓
Action Policy
  ↓
Exception Handler
  ↓
Response Generator
  ↓
Dialogue Orchestrator
  ↓
Post-call Builder
  ↓
Evaluation Runner
```

## 3. Giai đoạn 1 — Contract và skeleton

### Implement

```text
models.py
schemas.py
```

### Đọc

```text
AGENTS.md
docs/01_SHARED_CONTRACTS.md
docs/02_CATEGORY_SCHEMAS.md
```

### Acceptance criteria

- Có model cho input, output, state và final JSON.
- Schema đủ năm category.
- Không đổi tên field.
- Có schema validation tests.

## 4. Giai đoạn 2 — Intent routing

### Implement

```text
signal_extractor.py
emergency_detector.py
router.py
clarification.py
tests/test_router.py
```

### Đọc

```text
docs/01_SHARED_CONTRACTS.md
docs/03_INTENT_ROUTING.md
```

### Acceptance criteria

- Symptom-only không route sớm.
- Targeted clarification.
- G_1 đến G_5 có positive/negative tests.
- Emergency false positive tests.

## 5. Giai đoạn 3 — Field extraction và validation

### Implement

```text
extractor.py
validators.py
tests/test_extractor.py
tests/test_validators.py
```

### Đọc

```text
docs/01_SHARED_CONTRACTS.md
docs/02_CATEGORY_SCHEMAS.md
docs/04_DIALOGUE_STATE_AND_POLICY.md
```

### Acceptance criteria

- Multi-field extraction.
- Không bịa field.
- Critical fields có uncertainty handling.
- Field names đúng category.

## 6. Giai đoạn 4 — State và action policy

### Implement

```text
state_updater.py
action_policy.py
tests/test_state_updater.py
tests/test_action_policy.py
```

### Acceptance criteria

- No-reask.
- Correction.
- Missing field priority.
- Category change.
- Completion rule.

## 7. Giai đoạn 5 — Exception handling

### Implement

```text
correction_detector.py
exceptions.py
tests/test_exceptions.py
```

### Đọc

```text
docs/05_EXCEPTION_HANDLING.md
```

### Acceptance criteria

- Đủ tám exception cases.
- Failed turn handoff.
- Hang-up partial JSON.
- Emergency behavior.

## 8. Giai đoạn 6 — Dialogue orchestrator

### Implement

```text
response_generator.py
dialogue.py
post_call.py
tests/test_dialogue.py
```

### Acceptance criteria

- End-to-end transcript mode.
- Per-turn JSON hợp lệ.
- Final JSON đúng schema.
- Không để LLM tự phá state.

## 9. Giai đoạn 7 — Evaluation

### Implement

```text
evaluation/scenarios.json
evaluation/metrics.py
evaluation/run_evaluation.py
evaluation/report_generator.py
```

### Đọc

```text
docs/06_EVALUATION_SPEC.md
```

### Acceptance criteria

- Ít nhất hai scenario/category.
- Đủ exception coverage.
- Có turn-level evaluation.
- Có `results.json`.
- Có failure details.

## 10. Giai đoạn 8 — Voice integration

### Implement hoặc tích hợp

```text
pipeline.py
voice_app.py
```

### Đọc

```text
docs/07_VOICE_PIPELINE_INTERFACE.md
```

### Acceptance criteria

- Transcript mode vẫn chạy.
- Voice final transcript gọi dialogue engine.
- Barge-in metadata không phá flow.
- Hang-up event sinh partial JSON.

## 11. Quy trình Git đề xuất

- Mỗi module một branch nhỏ.
- Không trộn refactor lớn với feature.
- Mỗi PR phải ghi:
  - tài liệu đã đọc;
  - file đã sửa;
  - test đã chạy;
  - contract có thay đổi hay không;
  - limitation.

## 12. Definition of Done toàn hệ thống

- Đủ năm category.
- Đủ field đúng brief.
- Không premature route.
- Không hỏi lại field confirmed.
- Đủ tám exception cases.
- Final JSON hợp lệ.
- Transcript mode chạy.
- Voice integration chạy.
- Evaluation tự động.
- Failure report trung thực.

## 13. Giai đoạn Vehicle Model Recognition

Thực hiện sau data models và trước field extraction.

### Implement

```text
resources/vehicle_models.yaml
resources/asr_hotwords.txt
src/vinfast_callbot/vehicle_catalog.py
src/vinfast_callbot/vehicle_normalizer.py
src/vinfast_callbot/vehicle_matcher.py
tests/test_vehicle_matcher.py
```

### Đọc

```text
AGENTS.md
docs/01_SHARED_CONTRACTS.md
docs/02_CATEGORY_SCHEMAS.md
docs/03A_VEHICLE_MODEL_RECOGNITION.md
```

### Acceptance criteria

- load toàn bộ catalog;
- exact match đúng;
- alias match đúng;
- suy ra đúng vehicle type;
- fuzzy match phải xác nhận;
- không false-map model gần nhau;
- không map unknown model sang model gần nhất;
- correction model hoạt động;
- có parameterized tests cho toàn bộ canonical names.
