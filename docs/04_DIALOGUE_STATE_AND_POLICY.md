# 04 — Dialogue State and Policy

## 1. Mục tiêu

Quản lý hội thoại nhiều lượt theo cách deterministic và test được.

Dialogue policy phải quyết định:

- category đã rõ chưa;
- field nào đã có;
- field nào chưa xác nhận;
- field nào còn thiếu;
- action tiếp theo;
- khi nào handoff;
- khi nào finalize.

## 2. State machine

```text
idle
  ↓
routing
  ↓
collecting
  ↓
confirming
  ↓
completed
```

Nhánh khác:

```text
routing/collecting
  ├── troubleshooting
  ├── transferred
  ├── partial
  └── ended
```

## 3. Thứ tự xử lý mỗi turn

```text
1. Validate input event.
2. Detect empty hoặc unclear transcript.
3. Extract internal signals.
4. Detect correction.
5. Detect emergency.
6. Resolve category hoặc ask clarification.
7. Extract category fields.
8. Validate fields.
9. Update state.
10. Compute missing fields.
11. Select next action.
12. Render response.
13. Return per-turn JSON.
14. Build final JSON nếu kết thúc.
```

## 4. State update

### Quy tắc merge

- Giữ field cũ nếu câu mới không nhắc lại.
- Chỉ ghi đè khi có correction rõ ràng.
- Không ghi đè confirmed field bằng giá trị confidence thấp.
- Field uncertain đi vào `unconfirmed_fields`.
- Sau khi xác nhận, chuyển field sang `confirmed_fields`.
- Category đổi thì giữ các field chung hợp lệ.

### Ví dụ correction

```text
Khách: Xe của tôi là VF8.
Khách: Không phải, xe VF9.
```

State cuối:

```json
{
  "vehicle_model": "VF9"
}
```

## 5. Missing field policy

Chỉ tính missing fields sau khi category đã confirmed.

Ưu tiên hỏi:

```text
1. Safety hoặc emergency information
2. Field cần cho hành động ngay
3. Critical contact field
4. Vehicle/order identifier
5. Remaining required fields
6. Optional field
```

## 6. No-reask policy

Không hỏi lại field khi:

- field đã confirmed;
- khách không sửa field đó;
- category không đổi sang schema không tương thích;
- ASR metadata không báo field trước đó không chắc chắn.

Ví dụ:

```text
phone đã confirmed
→ không hỏi lại phone
```

## 7. Critical-field confirmation

Nên xác nhận riêng:

```text
phone
owner_phone
order_phone
license_plate_vin
order_code_dealer
current_odo
```

Không gom hai field khó nghe vào cùng một câu.

Không nên:

```text
Cho em xin số điện thoại và biển số hoặc VIN ạ.
```

Nên:

```text
Dạ anh/chị cho em xin số điện thoại liên hệ ạ.
```

Sau đó:

```text
Dạ anh/chị cho em xin biển số hoặc số VIN của xe ạ.
```

## 8. Dialogue actions

### `ASK_INTENT_CLARIFICATION`

Dùng khi category chưa đủ rõ.

### `ASK_MISSING_FIELD`

Dùng khi category đã confirmed và còn required field.

### `CONFIRM_UNCLEAR_FIELD`

Dùng khi ASR hoặc extractor không chắc chắn.

### `ACKNOWLEDGE_CORRECTION`

Dùng khi khách sửa field.

### `PROVIDE_REMOTE_STEP`

Dùng trong `G_5`.

### `ASK_REMOTE_STEP_RESULT`

Hỏi kết quả sau một bước xử lý.

### `CONFIRM_COLLECTED_INFORMATION`

Xác nhận thông tin trước khi hoàn tất nếu cần.

### `HANDLE_EMERGENCY`

Ưu tiên safety và handoff.

### `TRANSFER_TO_HUMAN`

Chuyển tư vấn viên.

### `FINALIZE_CALL`

Sinh final JSON.

### `END_PARTIAL_CALL`

Sinh partial JSON khi khách kết thúc sớm.

## 9. Action priority

```text
1. HANDLE_EMERGENCY
2. CONFIRM_UNCLEAR_FIELD
3. ASK_INTENT_CLARIFICATION
4. ACKNOWLEDGE_CORRECTION
5. TRANSFER_TO_HUMAN
6. ASK_MISSING_FIELD
7. PROVIDE_REMOTE_STEP
8. ASK_REMOTE_STEP_RESULT
9. CONFIRM_COLLECTED_INFORMATION
10. FINALIZE_CALL
```

## 10. Response rendering

Response Generator nhận action có cấu trúc, không tự quyết định flow.

Input:

```json
{
  "action": "ASK_MISSING_FIELD",
  "target_field": "phone",
  "reason": "Required field is missing"
}
```

Output:

```text
Dạ anh/chị cho em xin số điện thoại liên hệ ạ.
```

## 11. Multi-field input

Một lượt có thể chứa nhiều field:

```text
Tôi là Nguyễn Văn Nam, số 0900000000, xe VF8 bị chết máy ở đường Láng.
```

Extractor phải lấy toàn bộ field chắc chắn, sau đó policy hỏi field tiếp theo còn thiếu.

## 12. Final confirmation

Không cần đọc lại toàn bộ dữ liệu nếu cuộc gọi dài.

Nên xác nhận ngắn các thông tin hành động chính:

```text
Dạ em xin xác nhận anh Nam cần hỗ trợ cứu hộ xe VF8 đang chết máy tại đường Láng. Em sẽ chuyển thông tin để hỗ trợ anh ạ.
```

## 13. G_5 troubleshooting state

```json
{
  "troubleshooting": {
    "current_step": 1,
    "steps_attempted": [],
    "last_result": null,
    "resolved": false
  }
}
```

Flow:

```text
Collect context
  ↓
Provide one safe step
  ↓
Ask result
  ↓
Resolved?
  ├── Yes → finalize
  └── No → next safe step
               ↓
        Still unresolved?
          ├── No → finalize
          └── Yes → handoff hoặc service center
```

Không cung cấp hướng dẫn có rủi ro an toàn.

## 14. Completion rule

Một cuộc gọi hoàn tất khi:

- category confirmed;
- required fields đã có;
- critical fields cần xác nhận đã confirmed;
- không có emergency chưa xử lý;
- action cuối là finalize hoặc handoff hợp lệ.

## 15. Partial call

Khi khách kết thúc giữa chừng:

- `status = "partial"` hoặc `"ended"`;
- không hỏi thêm;
- final JSON vẫn có đầy đủ key;
- field thiếu là `null`;
- post-call summary phản ánh cuộc gọi chưa hoàn tất.

## 16. Unit tests bắt buộc

- no-reask;
- multi-field extraction;
- correction update;
- category change;
- partial JSON;
- critical-field confirmation;
- G_5 step progression;
- handoff after two failed turns.

## 17. Vehicle model state

```json
{
  "vehicle_model_state": {
    "raw_text": "green bus tám",
    "canonical_name": null,
    "vehicle_type": "car",
    "match_type": "ambiguous",
    "status": "needs_confirmation",
    "candidates": [
      "Green Bus 6M",
      "Green Bus 8M",
      "Green Bus 10M"
    ]
  }
}
```

Thêm action:

```text
CONFIRM_VEHICLE_MODEL
```

Policy:

- exact hoặc alias chắc chắn có thể ghi nhận;
- fuzzy hoặc ambiguous phải xác nhận;
- không hỏi lại model đã confirmed;
- khách sửa model thì cập nhật model mới;
- model ngoài catalog được lưu raw value sau khi khách xác nhận;
- không tự đổi model canonical thành variant gần nhất;
- category và model type xung đột phải được làm rõ.
