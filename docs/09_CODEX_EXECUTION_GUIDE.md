# 09 — Codex Execution Guide

## 1. Mục tiêu

Hướng dẫn cách giao task cho Codex để tránh mất context và tránh sửa lan sang module khác.

## 2. Nguyên tắc giao task

Mỗi task chỉ nên gồm:

1. `AGENTS.md`
2. `docs/00_PROJECT_OVERVIEW.md`
3. `docs/01_SHARED_CONTRACTS.md`
4. Một hoặc hai spec liên quan trực tiếp
5. Các file code phụ thuộc hiện có

Không yêu cầu Codex:

```text
Đọc toàn bộ repository và implement tất cả.
```

## 3. Prompt chuẩn cho task mới

```text
Đọc:
- AGENTS.md
- docs/00_PROJECT_OVERVIEW.md
- docs/01_SHARED_CONTRACTS.md
- <spec liên quan>

Nhiệm vụ:
- Implement <danh sách file>.
- Viết hoặc cập nhật <danh sách test>.

Ràng buộc:
- Không đổi public contract.
- Không đổi tên field trong brief.
- Không sửa module ngoài phạm vi.
- Không bịa dữ liệu.
- Chạy test trước khi hoàn thành.

Trước khi code:
1. Tóm tắt contract cần tuân theo.
2. Liệt kê file sẽ sửa.
3. Nêu điểm chưa rõ hoặc mâu thuẫn.

Sau khi code:
1. Tóm tắt thay đổi.
2. Liệt kê test đã chạy.
3. Báo limitation còn lại.
```

## 4. Prompt cho routing

```text
Đọc:
- AGENTS.md
- docs/01_SHARED_CONTRACTS.md
- docs/03_INTENT_ROUTING.md

Implement:
- src/vinfast_callbot/signal_extractor.py
- src/vinfast_callbot/emergency_detector.py
- src/vinfast_callbot/router.py
- src/vinfast_callbot/clarification.py
- tests/test_router.py

Acceptance criteria:
- "Xe tôi hết pin" không được route G_1.
- "Xe tôi hết pin, tôi cần cứu hộ" phải route G_1.
- Intent chưa rõ phải trả category = null.
- Clarification không được đọc cả 5 category.
- "Xe không khởi động" không phải emergency.
- "Xe tai nạn, có người bị thương" là emergency.

Không implement ASR, TTS, state updater hoặc evaluation trong task này.
```

## 5. Prompt cho state và policy

```text
Đọc:
- AGENTS.md
- docs/01_SHARED_CONTRACTS.md
- docs/02_CATEGORY_SCHEMAS.md
- docs/04_DIALOGUE_STATE_AND_POLICY.md

Implement:
- state_updater.py
- action_policy.py
- tests/test_state_updater.py
- tests/test_action_policy.py

Acceptance criteria:
- Không hỏi lại field đã confirmed.
- Correction ghi đè giá trị cũ.
- Missing fields đúng schema category.
- Critical field chưa rõ phải confirm.
- Không finalize khi còn required field, trừ partial/handoff.
```

## 6. Prompt cho exception handling

```text
Đọc:
- AGENTS.md
- docs/01_SHARED_CONTRACTS.md
- docs/05_EXCEPTION_HANDLING.md

Implement:
- correction_detector.py
- exceptions.py
- tests/test_exceptions.py

Yêu cầu:
- Đủ 8 exception cases.
- Sau 2 failed turns phải handoff.
- Hang-up sinh partial JSON.
- Emergency không được kích hoạt bởi lỗi xe thông thường.
```

## 7. Prompt cho evaluation

```text
Đọc:
- AGENTS.md
- docs/01_SHARED_CONTRACTS.md
- docs/02_CATEGORY_SCHEMAS.md
- docs/03_INTENT_ROUTING.md
- docs/05_EXCEPTION_HANDLING.md
- docs/06_EVALUATION_SPEC.md

Implement:
- evaluation/scenarios.json
- evaluation/metrics.py
- evaluation/run_evaluation.py
- evaluation/report_generator.py

Yêu cầu:
- Ít nhất 2 scenario/category.
- Expected theo từng turn.
- Có premature_routing_rate.
- Có no_reask_rate.
- Có emergency_false_positive_rate.
- Xuất results.json và failure details.
```

## 8. Quy tắc review Codex output

Kiểm tra:

- Có đổi field name không?
- Có route theo triệu chứng không?
- Có dùng category null khi chưa rõ không?
- Có hỏi menu dài không?
- Có field hallucination không?
- Có test cho failure case không?
- Có sửa file ngoài scope không?
- Có thay public contract không?
- Có chạy test thật không?

## 9. Khi Codex phát hiện mâu thuẫn

Codex phải:

1. dừng phần có mâu thuẫn;
2. chỉ rõ hai tài liệu hoặc code đang xung đột;
3. áp dụng source-of-truth order trong `AGENTS.md`;
4. không tự phát minh rule mới;
5. báo giả định nếu vẫn phải tiếp tục.

## 10. Khi contract cần thay đổi

Không sửa ngay.

Codex phải đề xuất:

```text
- Contract hiện tại
- Thay đổi mong muốn
- Lý do
- File bị ảnh hưởng
- Test cần cập nhật
- Có breaking change hay không
```

Chỉ sửa sau khi được xác nhận.

## 11. Context tối ưu cho mỗi task

Codex chỉ cần đọc:

```text
AGENTS.md
+ Shared Contracts
+ Category Schemas nếu có field
+ Một spec trực tiếp
+ Các file code phụ thuộc
```

Không nhét toàn bộ tài liệu vào mỗi prompt.

## 12. Prompt cho Vehicle Model Recognition

```text
Đọc:
- AGENTS.md
- docs/01_SHARED_CONTRACTS.md
- docs/02_CATEGORY_SCHEMAS.md
- docs/03A_VEHICLE_MODEL_RECOGNITION.md

Implement:
- resources/vehicle_models.yaml
- resources/asr_hotwords.txt
- src/vinfast_callbot/vehicle_catalog.py
- src/vinfast_callbot/vehicle_normalizer.py
- src/vinfast_callbot/vehicle_matcher.py
- tests/test_vehicle_matcher.py

Ràng buộc:
- Không sửa category routing trong task này.
- Không đổi final JSON contract.
- Không fuzzy-map model gần nhau nếu chưa xác nhận.
- Không map model ngoài catalog sang model gần nhất.
- Canonical name và vehicle type lấy từ catalog.
- Chạy toàn bộ test trước khi hoàn thành.

Acceptance criteria:
- "ép tám" → "VF 8"
- "Feliz hai" → "FELIZ II"
- "Green Bus tám mét" → "Green Bus 8M"
- "Zumo" không được map thành "ZGOO"
```
