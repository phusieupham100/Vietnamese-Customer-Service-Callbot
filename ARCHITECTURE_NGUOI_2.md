# KIẾN TRÚC CHO NGƯỜI 2

## Dialogue Logic, Exception Handling và Evaluation

## 1. Vai trò của Người 2

Người 2 chịu trách nhiệm xây dựng bộ não hội thoại của Vietnamese Customer Service Callbot.

Phần này quyết định:

* Khách hàng đang cần loại hỗ trợ nào.
* Cuộc gọi thuộc nhóm `G_1` đến `G_5` hay vẫn chưa đủ thông tin để phân loại.
* Thông tin nào đã được khách cung cấp.
* Thông tin nào đã được xác nhận.
* Field nào còn thiếu.
* Bot nên hỏi gì tiếp theo.
* Khi nào cần xác nhận lại thông tin.
* Khi nào cần chuyển nhân viên.
* Khi nào cuộc gọi hoàn tất.
* Final JSON cuối cuộc gọi được tạo như thế nào.
* Bot được đánh giá bằng những test case và metric nào.

Người 2 không phụ trách chính:

* Microphone.
* Audio streaming.
* ASR backend.
* TTS.
* Barge-in kỹ thuật.
* Local LLM server.
* CLI hoặc voice runtime.
* Logging latency ở tầng hệ thống.

Người 2 vẫn phải cung cấp interface ổn định để Người 1 kết nối voice pipeline vào dialogue engine.

---

# 2. Mục tiêu kỹ thuật

Phần của Người 2 phải bảo đảm:

* Phân loại đúng 5 nhóm nghiệp vụ.
* Không định tuyến chỉ dựa trên triệu chứng của xe.
* Không tự chọn `G_1` khi khách chỉ nói xe bị hỏng, hết pin hoặc không khởi động.
* Khi intent chưa rõ, hỏi một câu làm rõ ngắn và đúng trọng tâm.
* Không đọc danh sách cả 5 dịch vụ cho khách chọn.
* Trích xuất được nhiều field trong một lượt nói.
* Không hỏi lại field đã có và đã xác nhận.
* Cho phép khách sửa thông tin đã cung cấp.
* Không lưu dữ liệu không rõ hoặc không chắc chắn.
* Xác nhận các field dễ sai như số điện thoại, biển số hoặc VIN.
* Xử lý đủ 8 exception cases.
* Sinh JSON hợp lệ sau mỗi lượt.
* Sinh final JSON đúng schema của brief.
* Có evaluation theo từng turn và theo toàn bộ cuộc gọi.
* Ghi nhận failure cases trung thực.

---

# 3. Nguyên tắc thiết kế cốt lõi

## 3.1 Triệu chứng không phải là nhu cầu

Ví dụ:

```text
Xe tôi không khởi động được.
```

Câu này mới chỉ cho biết:

```text
vehicle_condition = "không khởi động được"
```

Chưa đủ để xác định khách muốn:

* Cứu hộ: `G_1`
* Bảo hành hoặc sửa chữa ô tô: `G_2`
* Bảo hành hoặc sửa chữa xe máy: `G_4`
* Hướng dẫn kiểm tra từ xa: `G_5`

Bot không được tự động chọn `G_1`.

Câu hỏi phù hợp:

```text
Dạ anh/chị có cần hỗ trợ cứu hộ ngay không ạ?
```

Nếu khách nói có:

```text
category = G_1
```

Nếu khách nói không và muốn được hướng dẫn:

```text
category = G_5
```

Nếu khách muốn đặt lịch kiểm tra:

```text
category = G_2 hoặc G_4
```

tùy loại phương tiện.

---

## 3.2 Category được xác định từ nhu cầu dịch vụ

Category phải dựa chủ yếu vào hành động khách muốn VinFast thực hiện:

```text
G_1: Cần cứu hộ, kéo xe hoặc hỗ trợ khẩn cấp tại chỗ.

G_2: Cần tư vấn bảo hành, sửa chữa hoặc trung tâm dịch vụ cho ô tô.

G_3: Cần hỗ trợ liên quan đến đơn hàng, giao xe, đặt cọc hoặc cập nhật đơn.

G_4: Cần tư vấn bảo hành, sửa chữa hoặc trung tâm dịch vụ cho xe máy điện.

G_5: Cần được hướng dẫn kiểm tra hoặc xử lý lỗi từ xa.
```

---

## 3.3 Chỉ hỏi thông tin còn thiếu

Bot phải:

* Giữ lại field đã có.
* Không hỏi lại field đã xác nhận.
* Trích xuất tất cả field khách tự cung cấp.
* Chỉ hỏi field tiếp theo còn thiếu.
* Ưu tiên một câu hỏi ngắn trong mỗi lượt.

---

## 3.4 Không để LLM toàn quyền điều khiển state

LLM có thể hỗ trợ:

* Phân tích intent.
* Trích xuất field.
* Nhận biết correction.
* Sinh câu trả lời tự nhiên.
* Sinh post-call summary.

Nhưng backend dialogue phải quyết định:

* Category đã được xác nhận chưa.
* Field nào được phép cập nhật.
* Field nào cần xác nhận.
* Missing fields.
* Failed turn count.
* Next action.
* Trạng thái kết thúc.
* Human handoff.
* Final JSON.

---

# 4. Kiến trúc tổng thể của Người 2

```text
Transcript + Session State + Conversation History
                       ↓
              NLU Signal Extractor
                       ↓
              Correction Detector
                       ↓
              Emergency Detector
                       ↓
                  Intent Router
              ┌────────┴────────┐
              ↓                 ↓
      Category confirmed   Needs clarification
              ↓                 ↓
         Field Extractor   Clarification Planner
              └────────┬────────┘
                       ↓
                Field Validator
                       ↓
                 State Updater
                       ↓
              Dialogue Action Policy
                       ↓
               Response Generator
                       ↓
                 Per-turn JSON
                       ↓
             Post-call JSON Builder
                       ↓
              Evaluation Framework
```

---

# 5. Cấu trúc module

```text
src/vinfast_callbot/
  schemas.py
  models.py
  prompts.py
  signal_extractor.py
  correction_detector.py
  emergency_detector.py
  router.py
  extractor.py
  validators.py
  state_updater.py
  action_policy.py
  clarification.py
  exceptions.py
  response_generator.py
  dialogue.py
  post_call.py

evaluation/
  scenarios.json
  metrics.py
  run_evaluation.py
  report_generator.py

tests/
  test_router.py
  test_extractor.py
  test_state_updater.py
  test_action_policy.py
  test_exceptions.py
  test_dialogue.py
```

## Trách nhiệm từng module

### `schemas.py`

* Định nghĩa 5 category.
* Giữ đúng field names trong brief.
* Định nghĩa required và optional fields.
* Định nghĩa thứ tự ưu tiên thu thập.
* Định nghĩa completion rule.

### `models.py`

Định nghĩa các object nội bộ:

* `DialogueInput`
* `DialogueOutput`
* `SessionState`
* `RoutingResult`
* `ExtractionResult`
* `DialogueAction`
* `FinalCallOutput`

### `signal_extractor.py`

Trích xuất tín hiệu phục vụ định tuyến:

* service goal
* vehicle type
* vehicle model
* vehicle condition
* can move
* explicit rescue request
* explicit warranty request
* explicit order request
* explicit remote support request
* urgency
* possible correction

### `correction_detector.py`

Nhận biết khi khách sửa thông tin:

```text
Không phải VF8, xe của tôi là VF9.
```

### `emergency_detector.py`

Nhận biết tình huống:

* Tai nạn.
* Có người bị thương.
* Cháy hoặc nguy cơ cháy.
* Nguy hiểm đến tính mạng.
* Xe ở vị trí nguy hiểm cần hỗ trợ khẩn cấp.

### `router.py`

Xác định:

* Category đã rõ chưa.
* Candidate categories.
* Cần hỏi thông tin phân biệt nào.
* Có đang định tuyến quá sớm hay không.

### `extractor.py`

Trích xuất các field đúng theo schema category.

### `validators.py`

Kiểm tra:

* Số điện thoại.
* Biển số hoặc VIN.
* ODO.
* Category.
* Enum values.
* Dữ liệu rỗng.
* Field không thuộc schema.

### `state_updater.py`

* Merge field mới vào state.
* Giữ field cũ.
* Ghi đè khi có correction rõ ràng.
* Quản lý confirmed và unconfirmed fields.
* Tính missing fields.

### `action_policy.py`

Quyết định bot làm gì tiếp theo.

### `clarification.py`

Tạo câu hỏi làm rõ ngắn, theo đúng thông tin còn thiếu.

### `exceptions.py`

Xử lý 8 exception cases.

### `response_generator.py`

Chuyển action có cấu trúc thành câu trả lời tự nhiên.

### `dialogue.py`

Orchestrator gọi các module theo đúng thứ tự.

### `post_call.py`

Sinh post-call output từ toàn bộ conversation.

---

# 6. Category schema đúng theo brief

Final JSON phải giữ nguyên field names dưới đây.

## 6.1 G_1 — Cứu hộ

### Mục tiêu

Nhận yêu cầu cứu hộ và chuẩn bị thông tin để điều phối trung tâm dịch vụ hoặc kéo xe.

### Fields

```text
full_name
phone
vehicle_model
license_plate_vin
vehicle_type
current_odo
current_location
city_name
vehicle_condition
```

### Completion rule

Hoàn tất khi:

* Category đã được xác nhận là `G_1`.
* Các field yêu cầu đã được thu thập hoặc cuộc gọi kết thúc theo exception.
* Thông tin quan trọng không còn ở trạng thái chưa xác nhận.

---

## 6.2 G_2 — Bảo hành và sửa chữa

### Mục tiêu

Tư vấn chính sách bảo hành hoặc sửa chữa và cung cấp thông tin trung tâm dịch vụ.

### Fields

```text
full_name
owner_phone
vehicle_model
vehicle_usage_type
license_plate_vin
service_center
vehicle_condition
```

---

## 6.3 G_3 — Đơn hàng

### Mục tiêu

Tư vấn trạng thái đơn hàng, giao xe, chuyển cọc hoặc cập nhật thông tin đơn.

### Fields

```text
full_name
order_phone
order_code_dealer
customer_type
```

Nhóm này không yêu cầu biển số hoặc VIN.

---

## 6.4 G_4 — Xe máy, bảo hành

### Mục tiêu

Tư vấn bảo hành hoặc sửa chữa xe máy điện và hướng dẫn đến trung tâm dịch vụ gần nhất.

### Fields

```text
full_name
phone
vehicle_line
license_plate_vin
current_location
vehicle_condition
```

---

## 6.5 G_5 — Hỗ trợ kỹ thuật từ xa

### Mục tiêu

Hướng dẫn khách kiểm tra hoặc khắc phục lỗi từ xa; chuyển sang trung tâm dịch vụ nếu không giải quyết được.

### Required fields

```text
full_name
phone
license_plate_vin
vehicle_line
vehicle_condition_details
```

### Optional field

```text
current_odo
```

`vehicle_condition_details` phải bao gồm phiên bản phần mềm nếu thông tin đó liên quan đến sự cố.

---

# 7. Phân biệt final fields và internal signals

Không đưa các field nội bộ vào `fields` của final JSON.

Ví dụ:

```json
{
  "fields": {
    "vehicle_condition": "xe không khởi động được"
  },
  "internal_state": {
    "can_move": false,
    "rescue_requested": null,
    "routing_status": "needs_clarification",
    "candidate_categories": ["G_1", "G_2", "G_5"]
  }
}
```

Các internal signals có thể gồm:

```text
service_goal
vehicle_type_detected
can_move
rescue_requested
remote_support_requested
repair_requested
warranty_requested
order_requested
intent_confidence
asr_uncertain
correction_detected
emergency_reason
```

Các signal này phục vụ dialogue logic nhưng không thay thế field trong brief.

---

# 8. Session State

```json
{
  "session_id": "call-001",
  "turn_id": 2,
  "category": null,
  "routing_status": "needs_clarification",
  "candidate_categories": ["G_1", "G_2", "G_5"],
  "service_goal": "unknown",
  "fields": {},
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

## Các trạng thái chính

```text
routing
collecting
confirming
troubleshooting
completed
partial
transferred
ended
```

## Routing status

```text
unresolved
needs_clarification
confirmed
```

---

# 9. Interface với Người 1

## 9.1 Input của Dialogue Engine

```json
{
  "session_id": "call-001",
  "turn_id": 1,
  "transcript": "Xe tôi bị chết máy trên cao tốc",
  "input_mode": "microphone",
  "history": [],
  "state": {
    "category": null,
    "routing_status": "unresolved",
    "fields": {},
    "confirmed_fields": [],
    "failed_turn_count": 0,
    "status": "routing"
  },
  "metadata": {
    "asr_confidence": 0.87,
    "was_interrupted": false
  }
}
```

## 9.2 Output của Dialogue Engine khi intent chưa rõ

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

## 9.3 Output sau khi khách xác nhận cứu hộ

```json
{
  "response_text": "Dạ em đã ghi nhận anh/chị cần hỗ trợ cứu hộ. Anh/chị cho em xin họ tên ạ.",
  "category": "G_1",
  "routing_status": "confirmed",
  "candidate_categories": [],
  "fields": {
    "full_name": null,
    "phone": null,
    "vehicle_model": null,
    "license_plate_vin": null,
    "vehicle_type": null,
    "current_odo": null,
    "current_location": "cao tốc",
    "city_name": null,
    "vehicle_condition": "xe chết máy"
  },
  "confirmed_fields": [
    "current_location",
    "vehicle_condition"
  ],
  "unconfirmed_fields": {},
  "missing_fields": [
    "full_name",
    "phone",
    "vehicle_model",
    "license_plate_vin",
    "vehicle_type",
    "current_odo",
    "city_name"
  ],
  "pending_field": "full_name",
  "next_action": "ASK_MISSING_FIELD",
  "status": "collecting",
  "failed_turn_count": 0,
  "transfer_to_human": false,
  "handoff_reason": null,
  "emergency": false,
  "should_end_call": false
}
```

---

# 10. Luồng xử lý mỗi lượt

```text
1. Nhận transcript và state hiện tại.
2. Kiểm tra transcript rỗng hoặc không rõ.
3. Trích xuất NLU signals.
4. Phát hiện correction.
5. Phát hiện emergency.
6. Nếu category chưa rõ:
   - chạy Intent Router;
   - xác nhận category hoặc tạo câu hỏi làm rõ.
7. Nếu category đã rõ:
   - trích xuất fields theo schema category.
8. Validate các field vừa trích xuất.
9. Đưa field chưa chắc chắn vào unconfirmed_fields.
10. Merge field hợp lệ vào state.
11. Tính missing_fields.
12. Action Policy chọn hành động tiếp theo.
13. Response Generator tạo câu trả lời.
14. Trả về per-turn JSON.
15. Nếu kết thúc cuộc gọi, tạo final JSON.
```

Pseudocode:

```python
def handle_turn(dialogue_input):
    state = dialogue_input.state
    transcript = dialogue_input.transcript

    if is_empty_or_unclear(transcript):
        return handle_unclear_input(state)

    signals = extract_signals(transcript, state, dialogue_input.history)
    correction = detect_correction(transcript, state)
    emergency = detect_emergency(transcript, signals)

    state = apply_correction_if_valid(state, correction)
    state = update_emergency_state(state, emergency)

    if not state.category:
        routing = route_intent(signals, state)

        if routing.needs_clarification:
            action = build_targeted_clarification(routing, state)
            return build_turn_output(state, action)

        state.category = routing.category
        state.routing_status = "confirmed"

    extracted_fields = extract_fields(
        transcript=transcript,
        category=state.category,
        current_state=state
    )

    validated_fields = validate_fields(extracted_fields)
    state = update_state(state, validated_fields)
    state.missing_fields = compute_missing_fields(state)

    action = select_next_action(state, signals)
    response = render_response(action, state)

    return build_turn_output(state, action, response)
```

---

# 11. Intent Router

## 11.1 Thứ tự định tuyến

```text
1. Emergency rõ ràng.
2. Nhu cầu đơn hàng.
3. Yêu cầu cứu hộ rõ ràng.
4. Yêu cầu hỗ trợ kỹ thuật từ xa rõ ràng.
5. Yêu cầu bảo hành hoặc sửa chữa.
6. Dùng loại phương tiện để phân biệt G_2 và G_4.
7. Nếu chỉ có triệu chứng, hỏi một câu ngắn để làm rõ.
```

## 11.2 Quy tắc cho G_1

Chọn trực tiếp `G_1` khi:

* Khách nói cần cứu hộ.
* Khách yêu cầu kéo xe.
* Khách yêu cầu đội hỗ trợ đến vị trí hiện tại.
* Khách xác nhận cần cứu hộ sau câu hỏi làm rõ.
* Emergency rõ ràng cần ưu tiên cứu hộ.

Không chọn `G_1` chỉ vì:

```text
Xe hết pin.
Xe chết máy.
Xe không khởi động.
Xe đang báo lỗi.
Xe không đi được.
```

Ví dụ:

```text
Khách: Xe tôi bị hết pin.
Bot: Dạ anh/chị có cần hỗ trợ cứu hộ ngay không ạ?
```

---

## 11.3 Quy tắc cho G_2

Chọn `G_2` khi:

* Khách hỏi bảo hành ô tô.
* Khách muốn sửa chữa ô tô.
* Khách muốn đặt lịch tại trung tâm dịch vụ.
* Khách hỏi lỗi có thuộc bảo hành không.
* Phương tiện đã được xác định là ô tô.

Ví dụ:

```text
Xe VF8 của tôi bị lỗi điều hòa, tôi muốn đặt lịch kiểm tra.
→ G_2
```

---

## 11.4 Quy tắc cho G_3

Chọn trực tiếp `G_3` khi liên quan đến:

* Trạng thái đơn hàng.
* Thời gian giao xe.
* Đặt cọc.
* Chuyển cọc.
* Mã đơn hoặc đại lý.
* Cập nhật thông tin đơn hàng.
* Loại khách hàng.

Ví dụ:

```text
Tôi muốn kiểm tra khi nào đơn xe của tôi được giao.
→ G_3
```

---

## 11.5 Quy tắc cho G_4

Chọn `G_4` khi:

* Phương tiện là xe máy điện.
* Khách cần bảo hành hoặc sửa chữa.
* Khách cần trung tâm dịch vụ gần nhất.

Ví dụ:

```text
Xe Feliz của tôi bị lỗi pin, tôi muốn mang đi bảo hành.
→ G_4
```

Nếu nhu cầu bảo hành đã rõ nhưng chưa biết loại xe:

```text
Dạ anh/chị đang sử dụng ô tô hay xe máy điện ạ?
```

---

## 11.6 Quy tắc cho G_5

Chọn `G_5` khi:

* Khách yêu cầu hướng dẫn kiểm tra.
* Khách hỏi cách thao tác.
* Khách muốn xử lý lỗi từ xa.
* Khách hỏi về phần mềm, ứng dụng hoặc kết nối và muốn được hướng dẫn.
* Khách đồng ý thử các bước xử lý từ xa.

Ví dụ:

```text
Màn hình xe bị treo, hướng dẫn tôi khởi động lại với.
→ G_5
```

Không chọn `G_5` chỉ vì xe có lỗi kỹ thuật.

---

# 12. Clarification Planner

Bot không được hỏi:

```text
Anh/chị muốn cứu hộ, sửa chữa, đơn hàng, bảo hành xe máy
hay hỗ trợ kỹ thuật từ xa ạ?
```

Bot chỉ hỏi tín hiệu còn thiếu.

## Khách chỉ mô tả lỗi xe

```text
Dạ anh/chị có cần hỗ trợ cứu hộ ngay không ạ?
```

## Khách muốn sửa chữa nhưng chưa rõ loại xe

```text
Dạ anh/chị đang sử dụng ô tô hay xe máy điện ạ?
```

## Khách gặp lỗi nhưng chưa rõ muốn sửa hay hướng dẫn

```text
Dạ anh/chị muốn em hướng dẫn kiểm tra trước không ạ?
```

## Câu nói hoàn toàn chung chung

```text
Dạ anh/chị cần hỗ trợ vấn đề gì với xe ạ?
```

## Quy tắc clarification

* Mỗi lượt chỉ hỏi một điểm phân biệt.
* Không đưa quá hai lựa chọn.
* Chỉ hỏi khi dữ liệu hiện tại chưa đủ.
* Không lặp lại cùng câu hỏi quá hai lần.
* Sau hai lượt vẫn không rõ, chuyển tư vấn viên.

---

# 13. Field Extraction

Field Extractor phải:

* Trích xuất nhiều field trong cùng một câu.
* Chỉ trích xuất field thuộc schema.
* Không bịa field không được khách nói.
* Không xóa field cũ khi câu mới không nhắc lại.
* Ghi nhận correction rõ ràng.
* Đưa dữ liệu chưa chắc chắn vào `unconfirmed_fields`.

Ví dụ:

```text
Tôi là Nguyễn Văn Nam, số 0900000000,
xe VF8 bị chết máy ở đường Láng, Hà Nội.
```

Kết quả cho `G_1`:

```json
{
  "full_name": "Nguyễn Văn Nam",
  "phone": "0900000000",
  "vehicle_model": "VF8",
  "current_location": "đường Láng",
  "city_name": "Hà Nội",
  "vehicle_condition": "xe chết máy"
}
```

---

# 14. Field Validation và Confirmation

## 14.1 Field cần ưu tiên xác nhận

* `phone`
* `owner_phone`
* `order_phone`
* `license_plate_vin`
* `order_code_dealer`
* `current_odo` khi ASR không chắc chắn

## 14.2 Không gom nhiều field khó nghe trong một câu

Không nên hỏi:

```text
Anh/chị cho em xin số điện thoại và biển số hoặc VIN ạ.
```

Nên hỏi:

```text
Dạ anh/chị cho em xin số điện thoại liên hệ ạ.
```

Sau khi xác nhận:

```text
Dạ anh/chị cho em xin biển số hoặc số VIN của xe ạ.
```

## 14.3 Trạng thái field

Mỗi field nên có metadata nội bộ:

```json
{
  "value": "0901234567",
  "status": "confirmed",
  "source_turn": 4,
  "confidence": 0.98,
  "corrected": false
}
```

Các trạng thái:

```text
missing
unconfirmed
confirmed
corrected
```

---

# 15. State Updater

## Quy tắc merge

* Field mới hợp lệ được thêm vào state.
* Field cũ được giữ nếu lượt mới không nhắc lại.
* Field chỉ bị ghi đè khi khách sửa rõ ràng.
* Không ghi đè bằng giá trị có confidence thấp.
* Sau correction, giá trị mới trở thành giá trị chính.
* Category đổi thì giữ các field chung hợp lệ.

Ví dụ:

```text
Khách: Biển số xe là 30A-12345.
Khách: Không phải, biển số đúng là 30A-54321.
```

State cuối:

```json
{
  "license_plate_vin": "30A-54321"
}
```

---

# 16. Dialogue Action Policy

Action Policy không sinh câu tự do. Nó chọn một action có cấu trúc.

Các action:

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
```

Ví dụ:

```json
{
  "action": "ASK_MISSING_FIELD",
  "target_field": "phone",
  "reason": "Phone is required and has not been collected."
}
```

## Thứ tự ưu tiên action

```text
1. Emergency.
2. Unclear critical field.
3. Intent clarification.
4. Correction acknowledgement.
5. Human handoff condition.
6. Missing required field.
7. Remote troubleshooting step.
8. Final confirmation.
9. Finalize.
```

---

# 17. Exception Handling

## 17.1 Missing field

* Hỏi đúng field còn thiếu.
* Không hỏi lại field đã xác nhận.
* Không chuyển `completed` khi thiếu required field, trừ trường hợp hang-up hoặc handoff.

---

## 17.2 Customer corrects information

* Nhận biết correction.
* Ghi đè giá trị cũ.
* Xác nhận ngắn.
* Không hỏi lại các field khác.

Ví dụ:

```text
Dạ em đã cập nhật dòng xe thành VF9 ạ.
```

---

## 17.3 Ambiguous intent

* Không tự chọn category.
* Xác định candidate categories.
* Hỏi một câu làm rõ ngắn.
* Không đọc menu 5 nhóm.

---

## 17.4 Out-of-scope query

* Thông báo phạm vi hỗ trợ ngắn gọn.
* Nếu gần một nhóm có sẵn, chuyển hướng.
* Nếu không phù hợp, đề nghị chuyển nhân viên.

---

## 17.5 Unclear hoặc garbled input

* Không lưu giá trị không chắc chắn.
* Yêu cầu khách nhắc lại đúng field bị mơ hồ.
* Tăng `failed_turn_count`.
* Với phone, biển số hoặc VIN phải xác nhận trước khi ghi.

---

## 17.6 Emergency detected

* Đặt `emergency = true`.
* Ưu tiên an toàn.
* Sử dụng hotline cứu hộ được cấu hình trong hệ thống.
* Bỏ qua field có độ ưu tiên thấp.
* Có thể chuyển người thật ngay.
* Không coi mọi lỗi xe là emergency.

Ví dụ emergency:

```text
Xe vừa tai nạn, có người bị thương.
```

Ví dụ không mặc định emergency:

```text
Xe không khởi động được.
```

---

## 17.7 Stuck sau hai lượt thất bại

Điều kiện:

```text
failed_turn_count >= 2
```

Hành động:

```json
{
  "transfer_to_human": true,
  "handoff_reason": "failed_understanding"
}
```

---

## 17.8 Customer hangs up giữa cuộc gọi

* Dừng hỏi thêm.
* Sinh partial JSON.
* Field thiếu để `null`.
* `status = "partial"` hoặc `"ended"`.
* Post-call vẫn được sinh từ hội thoại đã có.

---

# 18. Human Handoff

Các lý do chuyển người thật:

```text
emergency
failed_understanding
out_of_scope
customer_request
policy_requires_agent
remote_fix_failed
system_error
```

Output:

```json
{
  "transfer_to_human": true,
  "handoff_reason": "remote_fix_failed",
  "should_end_call": true
}
```

---

# 19. Response Generator

Response Generator nhận action và state, sau đó tạo câu trả lời.

## Nguyên tắc

* Ngắn gọn.
* Lịch sự.
* Tự nhiên.
* Không đọc tên field kỹ thuật.
* Không hỏi lại thông tin đã có.
* Không bịa chính sách hoặc kết quả xử lý.
* Không hứa điều hệ thống không thực hiện được.
* Mỗi lượt ưu tiên một câu hỏi.
* Có thể xác nhận nhẹ khi khách sửa thông tin.

Ví dụ:

```text
Dạ em đã cập nhật số điện thoại của anh/chị. Anh/chị cho em xin biển số hoặc số VIN của xe ạ.
```

---

# 20. G_5 Remote Troubleshooting Flow

`G_5` không chỉ thu thập field mà còn cần điều khiển các bước hướng dẫn.

```text
Collect required context
        ↓
Provide one troubleshooting step
        ↓
Ask customer for result
        ↓
Resolved?
   ├── Yes → confirm and finalize
   └── No  → provide next safe step
                     ↓
            Still unresolved?
               ├── No → finalize
               └── Yes → book service / handoff
```

State bổ sung:

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

Không đưa hướng dẫn có rủi ro an toàn.

---

# 21. Final JSON Builder

Final JSON phải bám đúng cấu trúc:

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

## Partial JSON

```json
{
  "category": "G_1",
  "fields": {
    "full_name": "Nguyễn Văn Nam",
    "phone": null,
    "vehicle_model": "VF8",
    "license_plate_vin": null,
    "vehicle_type": "car",
    "current_odo": null,
    "current_location": "đường Láng",
    "city_name": "Hà Nội",
    "vehicle_condition": "xe hết pin"
  },
  "post_call": {
    "short_summary": "Khách báo xe VF8 hết pin tại đường Láng nhưng kết thúc cuộc gọi trước khi cung cấp đủ thông tin.",
    "sentimental_analysis": "calm",
    "emergency": "no"
  }
}
```

Không đưa các field nội bộ như `candidate_categories`, `next_action` hoặc `failed_turn_count` vào final JSON.

---

# 22. Prompt Architecture

Nên tách prompt thành các tác vụ nhỏ.

## 22.1 Signal extraction prompt

Đầu ra:

```json
{
  "service_goal": "unknown",
  "vehicle_type": "car",
  "symptom": "không khởi động được",
  "explicit_rescue_request": false,
  "explicit_repair_request": false,
  "explicit_warranty_request": false,
  "explicit_order_request": false,
  "explicit_remote_support_request": false,
  "correction_detected": false
}
```

## 22.2 Field extraction prompt

Chỉ trích xuất field thuộc category đã xác nhận.

## 22.3 Post-call prompt

Sinh:

* `short_summary`
* `sentimental_analysis`
* `emergency`

## Quy tắc bắt buộc trong prompt

```text
A vehicle symptom is not the same as the requested service.

Do not classify a call as G_1 only because the vehicle is broken,
cannot start, has no battery, or shows an error.

When the requested service is unclear, return category = null.

Do not invent any customer information.

Do not overwrite a confirmed field unless the customer clearly corrects it.

Return valid JSON only.
```

---

# 23. Evaluation Scenarios

Nên xây dựng ít nhất:

```text
10 normal scenarios:
- 2 scenario cho mỗi category.

8 exception scenarios:
- 1 scenario cho mỗi exception case.

Các scenario bổ sung:
- symptom-only chưa được route.
- correction.
- multi-field input.
- phone hoặc plate ASR không rõ.
- chuyển intent.
- remote fix failed.
```

Mỗi scenario cần đánh giá theo từng turn.

Ví dụ:

```json
{
  "id": "ambiguous_breakdown_01",
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
  }
}
```

---

# 24. Evaluation Metrics

## Nhóm routing

```text
category_accuracy
premature_routing_rate
clarification_accuracy
routing_after_clarification_accuracy
emergency_false_positive_rate
```

### `premature_routing_rate`

Tỷ lệ bot chọn category khi thông tin chưa đủ.

Ví dụ lỗi:

```text
Xe tôi bị chết máy.
→ Bot chọn G_1 ngay.
```

### `emergency_false_positive_rate`

Tỷ lệ bot đánh dấu emergency sai.

---

## Nhóm field extraction

```text
field_exact_match
field_precision
field_recall
required_field_completion_rate
hallucinated_field_rate
critical_field_confirmation_rate
correction_update_rate
```

---

## Nhóm dialogue

```text
next_action_accuracy
dialogue_success_rate
no_reask_rate
average_turns_to_completion
handoff_accuracy
exception_handling_success_rate
```

---

## Nhóm output

```text
json_validity_rate
schema_compliance_rate
partial_json_correctness
post_call_completeness
```

---

## Nhóm latency

Người 2 nhận latency log từ Người 1 để tổng hợp:

```text
average_turn_latency_ms
p50_turn_latency_ms
p95_turn_latency_ms
```

---

# 25. Unit Tests quan trọng

## Router

```text
“Xe tôi hết pin”
→ category = null

“Xe tôi hết pin, tôi cần cứu hộ”
→ G_1

“Xe VF8 bị lỗi, tôi muốn đặt lịch kiểm tra”
→ G_2

“Bao giờ xe của tôi được giao?”
→ G_3

“Xe Feliz cần bảo hành”
→ G_4

“Hướng dẫn tôi khởi động lại màn hình”
→ G_5
```

## Emergency

```text
“Xe không khởi động”
→ emergency = false

“Xe tai nạn, có người bị thương”
→ emergency = true
```

## Correction

```text
“Xe VF8”
→ vehicle_model = VF8

“Không phải, xe VF9”
→ vehicle_model = VF9
```

## No-reask

Khi `phone` đã confirmed, bot không được hỏi lại `phone`.

## Partial JSON

Tất cả field chưa thu thập phải xuất `null`.

---

# 26. Tài liệu Người 2 cần bàn giao

```text
docs/dialogue_specification.md
docs/exception_handling.md
docs/evaluation_framework.md
docs/evaluation_report.md

src/vinfast_callbot/schemas.py
src/vinfast_callbot/models.py
src/vinfast_callbot/router.py
src/vinfast_callbot/extractor.py
src/vinfast_callbot/validators.py
src/vinfast_callbot/state_updater.py
src/vinfast_callbot/action_policy.py
src/vinfast_callbot/exceptions.py
src/vinfast_callbot/response_generator.py
src/vinfast_callbot/dialogue.py
src/vinfast_callbot/post_call.py

evaluation/scenarios.json
evaluation/metrics.py
evaluation/run_evaluation.py

tests/test_router.py
tests/test_dialogue.py
tests/test_exceptions.py
tests/test_validators.py
```

---

# 27. Interface ownership

## Người 2 sở hữu

* Category schema.
* Field schema.
* Session state logic.
* Dialogue output contract.
* Routing logic.
* Field collection.
* Exception behavior.
* Final JSON.
* Evaluation expected outputs.

## Người 1 sở hữu

* ASR output.
* Voice runtime.
* Session persistence kỹ thuật.
* TTS.
* Latency measurement.
* Pipeline invocation.

## Thay đổi cần review chung

* Tên field.
* Dialogue input/output contract.
* Status enum.
* Handoff reason.
* Final JSON schema.
* Error contract.

---

# 28. Checklist hoàn thành

Phần Người 2 được xem là hoàn thành khi:

* Schema giữ đúng field của brief.
* Đủ 5 category.
* Không route theo triệu chứng đơn thuần.
* Có targeted clarification.
* Không hỏi menu dài.
* Không hỏi lại field đã xác nhận.
* Cho phép sửa thông tin.
* Critical fields được xác nhận.
* Có action policy rõ ràng.
* Xử lý đủ 8 exception cases.
* Có human handoff.
* Có partial JSON.
* Final JSON đúng schema.
* Có ít nhất 2 scenario cho mỗi category.
* Có scenario cho exception cases.
* Có metric chống premature routing.
* Có metric no-reask.
* Có metric hallucination.
* Evaluation report dùng kết quả chạy thật.
* Failure cases và limitations được báo cáo trung thực.
