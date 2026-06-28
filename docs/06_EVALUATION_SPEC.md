# 06 — Evaluation Specification

## 1. Mục tiêu

Đánh giá callbot theo:

- category routing;
- field extraction;
- dialogue behavior;
- exception handling;
- JSON validity;
- latency;
- failure analysis.

Evaluation phải dùng output thật, không tự chấm bằng cảm giác.

## 2. Yêu cầu tối thiểu

- Ít nhất hai scenario cho mỗi category.
- Tối thiểu mười normal scenarios.
- Ít nhất ba exception scenarios.
- Khuyến nghị đủ tám exception scenarios.
- Có ít nhất một automated metric.
- Có latency per turn.
- Có failure analysis.

## 3. Scenario format

```json
{
  "id": "ambiguous_breakdown_01",
  "description": "Khách chỉ mô tả xe chết máy, chưa yêu cầu cứu hộ",
  "initial_state": {},
  "turns": [
    {
      "user": "Xe tôi bị chết máy trên cao tốc",
      "expected": {
        "category": null,
        "routing_status": "needs_clarification",
        "next_action": "ASK_INTENT_CLARIFICATION",
        "emergency": false
      }
    },
    {
      "user": "Có, tôi cần cứu hộ ngay",
      "expected": {
        "category": "G_1",
        "routing_status": "confirmed",
        "next_action": "ASK_MISSING_FIELD"
      }
    }
  ],
  "final_expected": {
    "category": "G_1"
  },
  "tags": ["G_1", "ambiguous_intent", "routing"]
}
```

## 4. Expected result theo turn

Mỗi turn có thể kiểm tra:

```text
category
routing_status
candidate_categories
next_action
pending_field
fields
confirmed_fields
missing_fields
emergency
transfer_to_human
handoff_reason
status
should_end_call
```

Không bắt buộc kiểm tra exact text của response trong mọi scenario. Có thể dùng:

- exact match với câu cố định;
- keyword/rule match;
- semantic rubric cho câu tự nhiên.

## 5. Routing metrics

### `category_accuracy`

```text
số scenario final category đúng / tổng scenario có category xác định
```

### `premature_routing_rate`

```text
số turn bị route khi chưa đủ bằng chứng / tổng turn ambiguous
```

Mục tiêu càng thấp càng tốt.

### `clarification_accuracy`

Tỷ lệ bot chọn đúng điểm cần làm rõ.

### `routing_after_clarification_accuracy`

Tỷ lệ route đúng sau khi khách trả lời câu làm rõ.

### `emergency_false_positive_rate`

Tỷ lệ bot đánh dấu emergency sai.

## 6. Field metrics

### `field_exact_match`

Tỷ lệ giá trị field trùng expected sau normalization.

### `field_precision`

Trong các field bot lưu, bao nhiêu field đúng.

### `field_recall`

Trong các field khách đã cung cấp, bot thu được bao nhiêu.

### `required_field_completion_rate`

Tỷ lệ required fields được thu thập khi call hoàn tất.

### `hallucinated_field_rate`

Tỷ lệ field bot lưu nhưng khách chưa cung cấp.

### `critical_field_confirmation_rate`

Tỷ lệ critical fields không chắc chắn được xác nhận trước khi lưu.

### `correction_update_rate`

Tỷ lệ correction được cập nhật đúng.

## 7. Dialogue metrics

### `next_action_accuracy`

Action bot chọn có đúng expected không.

### `dialogue_success_rate`

Scenario hoàn tất đúng mục tiêu và không vi phạm rule quan trọng.

### `no_reask_rate`

Tỷ lệ bot không hỏi lại field đã confirmed.

### `exception_handling_success_rate`

Tỷ lệ exception xử lý đúng.

### `handoff_accuracy`

Tỷ lệ handoff đúng lúc và đúng lý do.

### `average_turns_to_completion`

Số lượt trung bình để hoàn tất.

## 8. Output metrics

```text
json_validity_rate
schema_compliance_rate
partial_json_correctness
post_call_completeness
```

## 9. Latency metrics

Nhận từ log Người 1:

```text
asr_latency_ms
dialogue_latency_ms
tts_start_latency_ms
total_turn_latency_ms
barge_in_stop_latency_ms
```

Báo cáo:

```text
average
p50
p95
max
```

## 10. Scenario coverage đề xuất

### G_1

- explicit rescue;
- symptom-only rồi xác nhận cứu hộ.

### G_2

- hỏi bảo hành ô tô;
- đặt lịch sửa chữa.

### G_3

- trạng thái đơn;
- cập nhật thông tin đơn.

### G_4

- xe máy cần bảo hành;
- tìm trung tâm dịch vụ.

### G_5

- lỗi ứng dụng;
- troubleshooting nhiều bước rồi handoff.

### Exception

- missing field;
- correction;
- ambiguous intent;
- out-of-scope;
- unclear phone;
- emergency;
- two failed turns;
- hang-up.

### Voice-related

- ASR noise nhẹ;
- barge-in event;
- empty transcript.

## 11. Automated runner

Runner nên:

1. load scenarios;
2. reset state cho từng scenario;
3. chạy turn theo thứ tự;
4. lưu per-turn output;
5. so sánh expected;
6. tính metrics;
7. ghi failure detail;
8. xuất `results.json`;
9. sinh bảng tổng hợp cho report.

## 12. Failure record

```json
{
  "scenario_id": "ambiguous_breakdown_01",
  "turn_index": 0,
  "metric": "premature_routing",
  "expected": {
    "category": null
  },
  "actual": {
    "category": "G_1"
  },
  "reason": "Router treated symptom as rescue intent."
}
```

## 13. Evaluation report structure

```text
1. Objective
2. Scenario set
3. Metrics
4. Overall results
5. Results by category
6. Exception results
7. Latency breakdown
8. Failure cases
9. Limitations
10. Improvement plan
```

## 14. Acceptance gates đề xuất

Đây là mục tiêu nội bộ, không phải yêu cầu tuyệt đối của brief:

```text
json_validity_rate = 100%
schema_compliance_rate = 100%
premature_routing_rate = 0% trên scenario đã định nghĩa
emergency_false_positive_rate = 0% trên scenario đã định nghĩa
no_reask_rate ≥ 95%
exception_handling_success_rate ≥ 80%
```

Nếu chưa đạt, phải báo failure trung thực.

## 15. Không được làm

- Không chấm metric bằng tay rồi ghi như kết quả tự động.
- Không bỏ failure scenario khỏi report.
- Không dùng test set làm prompt few-shot mà không ghi rõ.
- Không chỉ đánh giá final category; phải đánh giá hành vi theo turn.

## 16. Vehicle model metrics

```text
vehicle_model_exact_match
vehicle_type_accuracy
vehicle_alias_resolution_rate
vehicle_model_confirmation_accuracy
unknown_model_false_mapping_rate
```

### Test groups

- tất cả canonical car models;
- tất cả canonical motorbike models;
- case-insensitive inputs;
- khoảng trắng khác nhau;
- dấu gạch ngang khác nhau;
- alias phát âm;
- model có chữ số;
- các cặp model dễ nhầm;
- unknown model;
- correction model;
- ASR confidence thấp.

### Test bắt buộc

```text
"ép tám" → VF 8
"Feliz" → Feliz
"Feliz hai" → FELIZ II
"Green Bus tám mét" → Green Bus 8M
"Zumo" → không map thành ZGOO
"Klara S" → không map thành KLARA S2
```

`unknown_model_false_mapping_rate` phải bằng 0 trên bộ scenario đã định nghĩa.
