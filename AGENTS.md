# AGENTS.md

## 1. Mục đích

Tài liệu này là hướng dẫn bắt buộc dành cho Codex và mọi AI coding agent khi làm việc trong repository Vietnamese Customer Service Callbot.

Không triển khai toàn bộ hệ thống chỉ dựa trên file này. Hãy đọc thêm các tài liệu chuyên biệt trong `docs/` theo bảng hướng dẫn ở mục 4.

## 2. Thứ tự ưu tiên của tài liệu

Khi các tài liệu có điểm chưa thống nhất, áp dụng thứ tự ưu tiên sau:

1. `docs/01_SHARED_CONTRACTS.md`
2. `docs/02_CATEGORY_SCHEMAS.md`
3. Tài liệu chuyên biệt của module đang triển khai
4. `docs/00_PROJECT_OVERVIEW.md`
5. Comment hoặc implementation hiện có trong code

Không tự sửa contract hoặc đổi tên field để phù hợp với code cũ. Code phải được sửa để phù hợp với contract.

## 3. Quy tắc nghiệp vụ bắt buộc

1. Giữ nguyên tên field trong brief.
2. Triệu chứng xe không đồng nghĩa với nhu cầu dịch vụ.
3. Không route `G_1` chỉ vì xe chết máy, hết pin, báo lỗi hoặc không khởi động.
4. Chỉ route `G_1` khi:
   - khách yêu cầu cứu hộ rõ ràng;
   - khách xác nhận cần cứu hộ;
   - hoặc có emergency rõ ràng.
5. Khi intent chưa đủ rõ:
   - `category = null`;
   - `routing_status = "needs_clarification"`;
   - hỏi một câu làm rõ ngắn, đúng điểm cần phân biệt.
6. Không đọc cả 5 category cho khách chọn.
7. Không bịa dữ liệu khách chưa cung cấp.
8. Field chưa có trong final JSON phải là `null`.
9. Không hỏi lại field đã được xác nhận.
10. Khách sửa thông tin thì phải cập nhật giá trị mới nhất.
11. Số điện thoại, biển số, VIN, mã đơn và ODO không rõ phải được xác nhận trước khi lưu.
12. Sau hai lượt không hiểu, đề nghị chuyển tư vấn viên.
13. Cuộc gọi kết thúc giữa chừng vẫn phải sinh partial JSON.
14. Mọi thay đổi logic phải có test tương ứng.

## 4. Tài liệu cần đọc theo module

| Module cần làm | Tài liệu bắt buộc |
|---|---|
| Toàn cảnh dự án | `docs/00_PROJECT_OVERVIEW.md` |
| Model, schema, contract | `docs/01_SHARED_CONTRACTS.md`, `docs/02_CATEGORY_SCHEMAS.md` |
| Intent routing | `docs/03_INTENT_ROUTING.md` |
| State và dialogue policy | `docs/04_DIALOGUE_STATE_AND_POLICY.md` |
| Exception handling | `docs/05_EXCEPTION_HANDLING.md` |
| Evaluation | `docs/06_EVALUATION_SPEC.md` |
| Giao tiếp với voice pipeline | `docs/07_VOICE_PIPELINE_INTERFACE.md` |
| Thứ tự triển khai | `docs/08_IMPLEMENTATION_PLAN.md` |
| Cách nhận task từ Codex | `docs/09_CODEX_EXECUTION_GUIDE.md` |

## 5. Phạm vi module

### Người 1 sở hữu chính

- Microphone stream
- Voice Activity Detection
- Streaming hoặc chunk ASR
- TTS
- Barge-in ở tầng audio
- Local LLM client
- Pipeline runtime
- Latency logging
- CLI và voice app

### Người 2 sở hữu chính

- Category schema
- Dialogue input/output contract
- Signal extraction
- Intent routing
- Field extraction
- Field validation
- State update
- Dialogue action policy
- Exception handling
- Response generation
- Post-call JSON
- Evaluation scenarios và metrics

Không sửa module thuộc người khác nếu task không yêu cầu rõ.

## 6. Quy tắc triển khai

- Ưu tiên hàm nhỏ, có type hints và test được độc lập.
- Tách phần quyết định hành động khỏi phần viết câu trả lời.
- Không để LLM tự quản lý toàn bộ state.
- LLM chỉ nên hỗ trợ:
  - signal extraction;
  - field extraction;
  - response rendering;
  - post-call summary.
- Backend phải kiểm soát:
  - category;
  - confirmed fields;
  - missing fields;
  - failed turn count;
  - next action;
  - handoff;
  - finalization.
- Output từ LLM phải được parse và validate trước khi cập nhật state.
- Không nuốt lỗi im lặng. Lỗi phải có fallback và log rõ.

## 7. Test bắt buộc trước khi hoàn thành task

Tối thiểu phải chạy:

```bash
python -m pytest
```

Nếu task liên quan evaluation:

```bash
python evaluation/run_evaluation.py
```

Nếu chưa có lệnh chạy thực tế trong repository, hãy báo rõ thay vì tự bịa.

## 8. Definition of Done

Một task chỉ được xem là hoàn tất khi:

- Không phá vỡ public contract.
- Có test cho happy path và failure path.
- Không đổi tên field trong brief.
- Không route theo triệu chứng đơn thuần.
- Không hỏi lại field đã xác nhận.
- JSON hợp lệ.
- Code chạy được với test hiện có.
- Các giả định hoặc limitation mới được ghi rõ.

## 9. Quy tắc nhận dạng model xe

- `docs/03A_VEHICLE_MODEL_RECOGNITION.md` là source of truth cho logic nhận dạng model.
- Catalog model là source of truth cho canonical name và loại phương tiện.
- Không tự tạo tên model ngoài catalog.
- Không fuzzy-map giữa các model gần nhau nếu chưa xác nhận.
- Model xe có thể suy ra `vehicle_type`, nhưng không tự quyết định category.
- Model ngoài catalog không được tự map sang model gần nhất.
- Nếu khách xác nhận model ngoài catalog, giữ raw value và đánh dấu nội bộ `unknown_confirmed`.
- Final JSON dùng canonical name khi match chắc chắn.
- Mọi thay đổi vehicle matcher phải có unit test.
