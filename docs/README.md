# Tài liệu thiết kế hệ thống

## Mục đích

Thư mục này chia kiến trúc thành các tài liệu nhỏ để Codex chỉ cần đọc đúng context của module đang triển khai, nhưng vẫn có một nguồn chuẩn chung để tránh mâu thuẫn.

## Thứ tự đọc khuyến nghị

1. `00_PROJECT_OVERVIEW.md`
2. `01_SHARED_CONTRACTS.md`
3. `02_CATEGORY_SCHEMAS.md`
4. Tài liệu chuyên biệt của module
5. `08_IMPLEMENTATION_PLAN.md`
6. `09_CODEX_EXECUTION_GUIDE.md`

## Danh sách tài liệu

| File | Nội dung |
|---|---|
| `00_PROJECT_OVERVIEW.md` | Mục tiêu, phạm vi và kiến trúc tổng thể |
| `01_SHARED_CONTRACTS.md` | Contract dùng chung, state, action và final JSON |
| `02_CATEGORY_SCHEMAS.md` | Field chính xác của `G_1` đến `G_5` |
| `03_INTENT_ROUTING.md` | Phân loại intent và targeted clarification |
| `03A_VEHICLE_MODEL_RECOGNITION.md` | Catalog model, normalization, alias matching và vehicle type inference |
| `04_DIALOGUE_STATE_AND_POLICY.md` | State machine, missing field và next action |
| `05_EXCEPTION_HANDLING.md` | Tám exception cases bắt buộc |
| `06_EVALUATION_SPEC.md` | Scenario format, metrics và acceptance gates |
| `07_VOICE_PIPELINE_INTERFACE.md` | Giao tiếp giữa voice runtime và dialogue engine |
| `08_IMPLEMENTATION_PLAN.md` | Thứ tự code và tích hợp |
| `09_CODEX_EXECUTION_GUIDE.md` | Prompt mẫu và cách giao task cho Codex |

## Source of truth

- Contract và enum: `01_SHARED_CONTRACTS.md`
- Category field schema: `02_CATEGORY_SCHEMAS.md`
- Routing rules: `03_INTENT_ROUTING.md`
- State transition: `04_DIALOGUE_STATE_AND_POLICY.md`
- Exception behavior: `05_EXCEPTION_HANDLING.md`

Không lặp lại hoặc đổi tên các field nghiệp vụ ở file khác.


## Vehicle model recognition

Khi triển khai hoặc sửa các module sau, Codex phải đọc `03A_VEHICLE_MODEL_RECOGNITION.md`:

```text
vehicle_catalog.py
vehicle_normalizer.py
vehicle_matcher.py
extractor.py
router.py
tests/test_vehicle_matcher.py
```

Field schema vẫn lấy từ `02_CATEGORY_SCHEMAS.md`; tên model canonical và quy tắc match lấy từ `03A_VEHICLE_MODEL_RECOGNITION.md`.

## Source of truth cho model xe

- Canonical model names và recognition rules: `03A_VEHICLE_MODEL_RECOGNITION.md`
- Category fields: `02_CATEGORY_SCHEMAS.md`
- Runtime catalog dự kiến: `resources/vehicle_models.yaml`
