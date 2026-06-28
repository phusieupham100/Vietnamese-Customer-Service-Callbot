# 05 — Exception Handling

## 1. Mục tiêu

Xử lý đầy đủ tám trường hợp ngoại lệ bắt buộc trong brief.

Mỗi exception phải có:

- trigger;
- expected action;
- state change;
- response behavior;
- expected JSON;
- test scenario.

## 2. Missing field

### Trigger

Category đã confirmed nhưng còn required field.

### Expected action

```text
ASK_MISSING_FIELD
```

### Behavior

- Chỉ hỏi field còn thiếu.
- Không hỏi lại field đã confirmed.
- Không chuyển completed khi còn thiếu field.

### Test

```text
phone đã có, license_plate_vin chưa có
→ hỏi license_plate_vin
→ không hỏi phone
```

## 3. Customer corrects information

### Trigger

Khách nói rõ giá trị trước đó sai.

Ví dụ:

```text
Không phải VF8, xe của tôi là VF9.
```

### Expected action

```text
ACKNOWLEDGE_CORRECTION
```

### State change

- cập nhật `vehicle_model = "VF9"`;
- đánh dấu corrected;
- giữ các field khác.

### Response

```text
Dạ em đã cập nhật dòng xe thành VF9 ạ.
```

## 4. Ambiguous intent

### Trigger

Khách mô tả vấn đề nhưng chưa nói nhu cầu.

Ví dụ:

```text
Xe tôi không khởi động được.
```

### Expected action

```text
ASK_INTENT_CLARIFICATION
```

### State change

```text
category = null
routing_status = needs_clarification
```

### Response

```text
Dạ anh/chị có cần hỗ trợ cứu hộ ngay không ạ?
```

Không đọc danh sách năm category.

## 5. Out-of-scope query

### Trigger

Nội dung không thuộc năm nhóm.

### Expected action

- acknowledge ngắn gọn;
- redirect nếu có nhóm gần nhất;
- hoặc handoff.

### Handoff reason

```text
out_of_scope
```

### Response mẫu

```text
Dạ nội dung này hiện chưa nằm trong phạm vi hỗ trợ tự động. Em xin phép chuyển anh/chị đến tư vấn viên ạ.
```

## 6. Unclear hoặc garbled input

### Trigger

- transcript rỗng;
- ASR confidence thấp;
- số điện thoại, biển số hoặc VIN không rõ;
- câu trả lời không liên quan đến pending field.

### Expected action

```text
REPEAT_OR_REPHRASE
```

hoặc:

```text
CONFIRM_UNCLEAR_FIELD
```

### State change

- không lưu dữ liệu chưa chắc chắn;
- tăng `failed_turn_count`.

### Response

```text
Dạ em chưa nghe rõ số điện thoại. Anh/chị vui lòng đọc lại từng số giúp em ạ.
```

## 7. Emergency detected

### Trigger

- tai nạn;
- có người bị thương;
- cháy;
- nguy cơ mất an toàn nghiêm trọng;
- yêu cầu cứu hộ khẩn cấp.

### Expected action

```text
HANDLE_EMERGENCY
```

### State change

```text
emergency = true
transfer_to_human = true hoặc theo policy
handoff_reason = emergency
```

### Behavior

- ưu tiên safety;
- dùng hotline được cấu hình;
- bỏ qua field ít ưu tiên;
- không coi mọi lỗi xe là emergency.

### Negative test

```text
Xe không khởi động.
→ emergency = false
```

## 8. Stuck after two failed turns

### Trigger

```text
failed_turn_count >= 2
```

### Expected action

```text
TRANSFER_TO_HUMAN
```

### Handoff reason

```text
failed_understanding
```

### Response

```text
Dạ em xin phép chuyển anh/chị đến tư vấn viên để được hỗ trợ chính xác hơn ạ.
```

## 9. Customer hangs up mid-call

### Trigger

- event `hangup`;
- khách nói muốn gọi lại sau;
- khách kết thúc trước khi đủ field.

### Expected action

```text
END_PARTIAL_CALL
```

### State change

```text
status = partial hoặc ended
should_end_call = true
```

### Output

- sinh partial JSON;
- field thiếu là `null`;
- post-call summary phản ánh chưa hoàn tất.

## 10. Exception bổ sung nên hỗ trợ

### Customer requests agent

```text
handoff_reason = customer_request
```

### Remote fix failed

```text
handoff_reason = remote_fix_failed
```

### System error

```text
handoff_reason = system_error
```

### Silence

Có thể tính như unclear input, nhưng không tăng lỗi quá nhanh nếu chỉ là khoảng nghỉ ngắn.

### Barge-in

Voice runtime dừng TTS. Dialogue engine nhận event metadata và xử lý câu nói mới như một turn bình thường.

## 11. Test matrix tối thiểu

| Case | Expected |
|---|---|
| Missing field | Chỉ hỏi field thiếu |
| Correction | Ghi đè giá trị cũ |
| Ambiguous intent | Category null, hỏi ngắn |
| Out-of-scope | Redirect hoặc handoff |
| Garbled phone | Không lưu, hỏi lại |
| Emergency | Ưu tiên safety |
| Two failed turns | Handoff |
| Hang-up | Partial JSON |

## 12. Acceptance criteria

- Đủ tám exception cases.
- Mỗi case có test.
- Không crash pipeline.
- Không bịa dữ liệu.
- Không hỏi lại field đã confirmed.
- Không đánh dấu emergency sai với lỗi xe thông thường.

## 13. Unclear hoặc unknown vehicle model

### Trigger

- ASR nghe không rõ model;
- thiếu hậu tố số hoặc variant;
- nhiều candidate gần nhau;
- model ngoài catalog;
- model mới xung đột với model đã confirmed.

### Expected action

```text
CONFIRM_VEHICLE_MODEL
```

### Behavior

- không tự chọn candidate có similarity cao nhất;
- chỉ hỏi một câu ngắn;
- không đọc danh sách dài;
- model ngoài catalog không được map sang model gần nhất;
- nếu khách xác nhận model lạ, lưu raw value với trạng thái `unknown_confirmed`.

### Ví dụ

```text
ASR: Green Bus tám...
Bot: Dạ anh/chị đang sử dụng Green Bus 8M đúng không ạ?
```

```text
Khách: Xe Zumo.
Bot: Dạ em xin xác nhận tên dòng xe là Zumo đúng không ạ?
```

Sau khi khách xác nhận `Zumo`, không map sang `ZGOO`.
