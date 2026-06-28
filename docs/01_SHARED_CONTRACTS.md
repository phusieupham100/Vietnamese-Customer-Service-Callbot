# 01 — Shared Contracts

## 1. Mục đích

Đây là source of truth cho interface giữa voice pipeline, dialogue engine và evaluation.

Không đổi tên field, enum hoặc cấu trúc public nếu chưa được cả hai người review.

## 2. DialogueInput

```json
{
  "session_id": "call-001",
  "turn_id": 3,
  "transcript": "Xe tôi bị chết máy trên cao tốc",
  "input_mode": "microphone",
  "history": [
    {
      "role": "user",
      "content": "Xe tôi đang có vấn đề"
    },
    {
      "role": "assistant",
      "content": "Dạ anh/chị có cần hỗ trợ cứu hộ ngay không ạ?"
    }
  ],
  "state": {},
  "metadata": {
    "asr_confidence": 0.87,
    "is_final_transcript": true,
    "was_interrupted": false,
    "event_type": "user_utterance"
  }
}
```

## 3. DialogueOutput

```json
{
  "response_text": "Dạ anh/chị có cần hỗ trợ cứu hộ ngay không ạ?",
  "category": null,
  "routing_status": "needs_clarification",
  "candidate_categories": ["G_1", "G_2", "G_5"],
  "fields": {},
  "confirmed_fields": [],
  "unconfirmed_fields": {
    "vehicle_condition": "xe chết máy",
    "current_location": "cao tốc"
  },
  "missing_fields": [],
  "pending_field": "rescue_needed",
  "next_action": "ASK_INTENT_CLARIFICATION",
  "status": "routing",
  "failed_turn_count": 0,
  "transfer_to_human": false,
  "handoff_reason": null,
  "emergency": false,
  "should_end_call": false
}
```

## 4. SessionState

```json
{
  "session_id": "call-001",
  "turn_id": 3,
  "category": null,
  "routing_status": "needs_clarification",
  "candidate_categories": ["G_1", "G_2", "G_5"],
  "service_goal": "unknown",
  "fields": {},
  "field_states": {},
  "confirmed_fields": [],
  "unconfirmed_fields": {},
  "missing_fields": [],
  "pending_field": "rescue_needed",
  "last_action": "ASK_INTENT_CLARIFICATION",
  "failed_turn_count": 0,
  "clarification_count": 1,
  "emergency": false,
  "emergency_reason": null,
  "transfer_to_human": false,
  "handoff_reason": null,
  "status": "routing",
  "conversation_history": []
}
```

## 5. Routing status

```text
unresolved
needs_clarification
confirmed
```

## 6. Call status

```text
idle
routing
collecting
confirming
troubleshooting
completed
partial
transferred
ended
```

## 7. Dialogue actions

```text
ASK_INTENT_CLARIFICATION
ASK_MISSING_FIELD
CONFIRM_UNCLEAR_FIELD
ACKNOWLEDGE_CORRECTION
PROVIDE_REMOTE_STEP
ASK_REMOTE_STEP_RESULT
CONFIRM_COLLECTED_INFORMATION
HANDLE_EMERGENCY
TRANSFER_TO_HUMAN
FINALIZE_CALL
END_PARTIAL_CALL
REPEAT_OR_REPHRASE
```

## 8. Handoff reasons

```text
emergency
failed_understanding
out_of_scope
customer_request
policy_requires_agent
remote_fix_failed
system_error
rescue_dispatch
```

## 9. FieldState

```json
{
  "value": "0901234567",
  "status": "confirmed",
  "source_turn": 4,
  "confidence": 0.98,
  "corrected": false
}
```

Field status:

```text
missing
unconfirmed
confirmed
corrected
```

## 10. RoutingResult

```json
{
  "category": null,
  "routing_status": "needs_clarification",
  "confidence": 0.61,
  "candidate_categories": ["G_1", "G_2", "G_5"],
  "missing_discriminator": "rescue_needed",
  "clarification_question": "Dạ anh/chị có cần hỗ trợ cứu hộ ngay không ạ?",
  "evidence": [
    "vehicle cannot start",
    "customer has not requested a specific service"
  ]
}
```

## 11. ExtractionResult

```json
{
  "fields": {
    "vehicle_condition": "xe không khởi động được"
  },
  "internal_signals": {
    "can_move": null,
    "explicit_rescue_request": false,
    "explicit_remote_support_request": false
  },
  "uncertain_fields": {},
  "corrections": []
}
```

## 12. Error contract

Dialogue engine không được crash pipeline khi LLM hoặc parser lỗi.

```json
{
  "error_code": "LLM_OUTPUT_INVALID",
  "recoverable": true,
  "fallback_action": "REPEAT_OR_REPHRASE",
  "response_text": "Dạ em chưa nghe rõ thông tin vừa rồi, anh/chị vui lòng nói lại giúp em ạ."
}
```

Error code đề xuất:

```text
EMPTY_TRANSCRIPT
UNCLEAR_TRANSCRIPT
LLM_TIMEOUT
LLM_OUTPUT_INVALID
SCHEMA_VALIDATION_FAILED
UNSUPPORTED_EVENT
INTERNAL_DIALOGUE_ERROR
```

## 13. FinalCallOutput

```json
{
  "category": "G_1",
  "fields": {
    "full_name": "Nguyễn Văn Nam",
    "phone": "0900000000",
    "vehicle_model": "VF8",
    "license_plate_vin": "30A-12345",
    "vehicle_type": "car",
    "current_odo": 25000,
    "current_location": "đường Láng",
    "city_name": "Hà Nội",
    "vehicle_condition": "xe hết pin"
  },
  "post_call": {
    "short_summary": "Khách hàng báo xe VF8 hết pin tại đường Láng và yêu cầu hỗ trợ cứu hộ.",
    "sentimental_analysis": "urgent",
    "emergency": "no"
  }
}
```

## 14. Quy tắc final JSON

- Chỉ chứa `category`, `fields`, `post_call`.
- Field chưa có phải là `null`.
- Không đưa internal signals vào final JSON.
- Không đưa `candidate_categories`, `next_action`, `failed_turn_count` hoặc confidence vào final JSON.
- `emergency` trong `post_call` dùng giá trị `"yes"` hoặc `"no"`.
- `sentimental_analysis` là string ngắn như `calm`, `frustrated`, `urgent`.
- `short_summary` dài một đến hai câu.

## 15. Versioning

Contract nên có version ở tầng code hoặc config:

```text
dialogue_contract_version = "1.0"
```

Mọi thay đổi breaking change phải:

1. cập nhật tài liệu;
2. cập nhật test;
3. cập nhật cả pipeline và evaluation;
4. được review chung.

## 16. VehicleMatchResult

```json
{
  "raw_text": "ép tám",
  "canonical_name": "VF 8",
  "vehicle_type": "car",
  "match_type": "alias",
  "confidence": 0.98,
  "status": "confirmed",
  "candidates": []
}
```

`match_type`:

```text
exact
alias
fuzzy
ambiguous
unknown
```

`status`:

```text
confirmed
needs_confirmation
unknown
unknown_confirmed
```

`VehicleMatchResult` là object nội bộ. Không đưa object này vào final JSON.

## 17. Contract rule cho model xe

- Chỉ final transcript mới được commit model.
- Fuzzy hoặc ambiguous match không được cập nhật trực tiếp field.
- Model ngoài catalog phải được xác nhận trước khi lưu raw value.
- Model canonical được map vào field theo `02_CATEGORY_SCHEMAS.md`.
