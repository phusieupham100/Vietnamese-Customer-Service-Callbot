# TEAM 7-DAY EXECUTION PLAN

## Vietnamese Customer Service Callbot

## 1. Mục tiêu dự án

Trong 7 ngày, nhóm 2 người xây dựng một Vietnamese Customer Service Callbot có khả năng:

* Nhận đầu vào từ transcript, audio file hoặc microphone.
* Sử dụng ASR để chuyển giọng nói tiếng Việt thành transcript.
* Phân loại cuộc gọi vào một trong 5 nhóm:

  * `G_1`: Cứu hộ.
  * `G_2`: Bảo hành và sửa chữa.
  * `G_3`: Đơn hàng.
  * `G_4`: Bảo hành xe máy.
  * `G_5`: Hỗ trợ kỹ thuật từ xa.
* Thu thập đầy đủ các trường thông tin bắt buộc.
* Quản lý hội thoại nhiều lượt.
* Chỉ hỏi các thông tin còn thiếu.
* Cho phép khách hàng sửa lại thông tin.
* Xử lý các trường hợp ngoại lệ.
* Sinh phản hồi bằng văn bản.
* Sinh final JSON sau khi kết thúc cuộc gọi.
* Có evaluation framework, evaluation report, README và `requirements.txt`.
* Đo latency theo từng lượt hội thoại.

TTS là phần bonus, chỉ thực hiện khi core bot, evaluation và documentation đã hoàn thiện.

---

# 2. Nguyên tắc phân chia công việc

Hai người phát triển song song theo hai nhánh:

* **Người 1:** phụ trách hạ tầng kỹ thuật và làm cho hệ thống chạy end-to-end.
* **Người 2:** phụ trách logic hội thoại, hành vi của bot và đánh giá chất lượng.

Ranh giới chính:

```text
Người 1:
Input, ASR, LLM backend, pipeline, integration, demo

Người 2:
Schema, Dialogue Manager, exception handling, evaluation, documents
```

Hai người phải thống nhất interface dữ liệu từ đầu để có thể làm việc độc lập mà không phải chờ nhau.

---

# 3. Phân công Người 1

## Vai trò

**Pipeline, ASR, LLM Backend, Integration và Demo**

Người 1 chịu trách nhiệm xây dựng phần kỹ thuật để toàn bộ hệ thống có thể chạy được.

## Công việc chính

### 3.1. Repository và môi trường

* Thiết kế repository structure.
* Thiết lập môi trường Python.
* Quản lý dependency.
* Chuẩn bị:

  * `requirements.txt`
  * `.env.example`
  * file cấu hình model
  * hướng dẫn cài đặt
* Bảo đảm không có API key hoặc token trong source code.

### 3.2. Input modes

Xây dựng ba cách đưa dữ liệu vào hệ thống:

1. Transcript mode.
2. Audio file mode.
3. Microphone mode.

Transcript mode phải được hoàn thành trước để Người 2 có thể kiểm thử dialogue mà không phụ thuộc ASR.

### 3.3. ASR

* Tích hợp một ASR model tiếng Việt như:

  * Faster-Whisper.
  * Whisper.
  * PhoWhisper.
  * Model tương đương.
* Xây dựng ASR adapter:

  * Audio input.
  * Audio preprocessing.
  * Speech-to-text.
  * Transcript normalization.
* Xử lý:

  * Audio rỗng.
  * Transcript rỗng.
  * Không nhận diện được giọng nói.
  * Lỗi tải hoặc chạy model.
* Đo ASR latency.

### 3.4. LLM backend

* Tích hợp local LLM backend hoặc inference backend:

  * Ollama.
  * llama.cpp.
  * Hugging Face.
  * vLLM hoặc giải pháp tương đương.
* Xử lý:

  * Timeout.
  * Model không phản hồi.
  * JSON không hợp lệ.
  * Retry khi cần thiết.
* Cung cấp interface đơn giản để Dialogue Manager gọi LLM.

### 3.5. Pipeline integration

Kết nối toàn bộ pipeline:

```text
Transcript / Audio / Microphone
        ↓
       ASR
        ↓
    Transcript
        ↓
Dialogue Manager
        ↓
 Text Response
        ↓
 Updated State
        ↓
   Final JSON
```

Người 1 không chịu trách nhiệm chính thiết kế hội thoại, mà chịu trách nhiệm kết nối Dialogue Manager do Người 2 phát triển vào pipeline.

### 3.6. Session và logging

* Quản lý `session_id`.
* Lưu conversation history.
* Lưu conversation state.
* Ghi log từng lượt:

  * Input transcript.
  * Category dự đoán.
  * Field đã thu thập.
  * Response.
  * Error.
  * Latency.
* Hỗ trợ xuất log phục vụ evaluation.

### 3.7. JSON validation

* Validate output theo schema.
* Bảo đảm final JSON luôn có:

  * `category`
  * `fields`
  * `post_call`
* Trường chưa thu thập được phải là `null`.
* Có fallback khi LLM trả sai format.

### 3.8. Evaluation runner

Người 1 phụ trách phần kỹ thuật chạy evaluation:

* Đọc test scenarios từ file.
* Chạy nhiều hội thoại tự động.
* Thu predicted output.
* Đo latency.
* Xuất:

  * `results.json`
  * hoặc `results.csv`
* Hỗ trợ Người 2 tổng hợp metrics.

### 3.9. CLI và demo

Xây dựng CLI hoặc app đơn giản với các chế độ:

```text
--interactive
--transcript
--audio
--microphone
--evaluation
```

Demo phải dễ chạy và không yêu cầu chỉnh code thủ công.

### Đầu ra Người 1 cần hoàn thành

* Repository chạy được.
* Transcript input.
* Audio file input.
* Microphone input nếu môi trường hỗ trợ.
* ASR module.
* LLM client.
* Pipeline integration.
* Session manager.
* Logging và latency tracking.
* JSON validator.
* Evaluation runner.
* CLI hoặc demo app.
* Setup instructions.
* TTS nếu còn thời gian.

---

# 4. Phân công Người 2

## Vai trò

**Dialogue Manager, Schema, Exception Handling, Evaluation và Documentation**

Người 2 chịu trách nhiệm xây dựng logic quyết định bot phải hiểu gì, hỏi gì, phản hồi thế nào và đánh giá bot có hoạt động đúng hay không.

## Công việc chính

### 4.1. Phân tích yêu cầu

* Đọc và tóm tắt brief.
* Xác định mục tiêu từng category.
* Xác định required fields và optional fields.
* Viết checklist hành vi bắt buộc của bot.

### 4.2. Category và field schema

Định nghĩa schema cho 5 nhóm.

#### `G_1` — Cứu hộ

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

#### `G_2` — Bảo hành và sửa chữa

```text
full_name
owner_phone
vehicle_model
vehicle_usage_type
license_plate_vin
service_center
vehicle_condition
```

#### `G_3` — Đơn hàng

```text
full_name
order_phone
order_code_dealer
customer_type
```

#### `G_4` — Bảo hành xe máy

```text
full_name
phone
vehicle_line
license_plate_vin
current_location
vehicle_condition
```

#### `G_5` — Hỗ trợ kỹ thuật từ xa

```text
full_name
phone
license_plate_vin
vehicle_line
current_odo
vehicle_condition_details
```

Trong `G_5`, `current_odo` là optional.

### 4.3. Dialogue Manager

Người 2 chịu trách nhiệm thiết kế và implement Dialogue Manager.

Dialogue Manager phải thực hiện được:

* Phân loại category.
* Trích xuất thông tin từ câu nói khách hàng.
* Cập nhật conversation state.
* Xác định các field còn thiếu.
* Chọn câu hỏi tiếp theo.
* Không hỏi lại field đã có.
* Thu nhận nhiều field trong một lượt nói.
* Ghi nhận thông tin khách hàng sửa lại.
* Xác định khi nào đủ thông tin.
* Xác nhận thông tin quan trọng.
* Kết thúc hội thoại đúng lúc.
* Sinh final JSON.
* Sinh post-call information.

### 4.4. Prompt engineering

Viết và quản lý prompt cho:

* Intent classification.
* Field extraction.
* Dialogue state update.
* Response generation.
* Post-call summary.
* Sentiment analysis.
* Emergency detection.

Prompt phải yêu cầu:

* Không tự bịa dữ liệu.
* Dữ liệu chưa biết trả về `null`.
* Không tự suy đoán category khi intent mơ hồ.
* Chỉ hỏi field còn thiếu.
* Ưu tiên safety khi có emergency.
* Output theo JSON schema quy định.

### 4.5. Conversation flow

Thiết kế flow riêng cho từng category.

Mỗi flow cần có:

```text
Nhận diện intent
      ↓
Khởi tạo category
      ↓
Trích xuất các field đã có
      ↓
Xác định field còn thiếu
      ↓
Hỏi từng field còn thiếu
      ↓
Xác nhận thông tin quan trọng
      ↓
Thực hiện hành động hoặc hướng dẫn
      ↓
Final JSON
```

### 4.6. Exception handling

Thiết kế và implement chiến lược cho đầy đủ 8 tình huống.

#### Missing field

* Chỉ hỏi field còn thiếu.
* Không hỏi lại dữ liệu đã xác nhận.

#### Customer corrects info

* Xác nhận đã ghi nhận chỉnh sửa.
* Ghi đè giá trị cũ.
* Tiếp tục từ state hiện tại.

#### Ambiguous intent

* Hỏi một câu làm rõ.
* Không tự route khi chưa đủ thông tin.

#### Out-of-scope query

* Thông báo phạm vi hỗ trợ.
* Đề nghị chuyển nhân viên nếu phù hợp.

#### Unclear or garbled input

* Yêu cầu khách xác nhận lại dữ liệu chưa rõ.
* Không ghi dữ liệu chưa chắc chắn vào state.

#### Emergency detected

* Ưu tiên an toàn.
* Dừng thu thập các field ít quan trọng.
* Hướng dẫn liên hệ cứu hộ hoặc nhân viên.
* Đánh dấu `emergency = yes`.

#### Stuck after two or more failed turns

* Theo dõi số lượt không hiểu.
* Sau ít nhất hai lượt thất bại, đề nghị chuyển nhân viên.

#### Customer hangs up mid-call

* Sinh partial JSON.
* Giữ lại field đã có.
* Gán các field còn thiếu bằng `null`.

### 4.7. Test scenarios

Xây dựng bộ test gồm:

* Ít nhất 2 scenarios cho mỗi category.
* Tối thiểu 10 normal scenarios.
* Có ít nhất 3 exception scenarios.
* Nên kiểm thử đủ cả 8 exception cases.
* Có happy path.
* Có ambiguous intent.
* Có correction.
* Có emergency.
* Có hang-up.
* Có input không rõ.
* Có khách cung cấp nhiều field trong một câu.

Mỗi scenario cần định nghĩa:

```text
scenario_id
category_expected
conversation_turns
expected_fields
expected_final_status
expected_exception_behavior
```

### 4.8. Metrics

Người 2 định nghĩa và tính các metrics:

* Category Accuracy.
* Field Extraction Accuracy.
* Required-field Completion Rate.
* JSON Validity Rate.
* Dialogue Success Rate.
* Exception Handling Success Rate.
* No-Reask Rate.
* Average Turns per Successful Call.
* Average Latency per Turn.
* P50 và P95 latency nếu đủ dữ liệu.

### 4.9. Failure analysis

Phân tích các lỗi theo nhóm:

* ASR error.
* Intent classification error.
* Field extraction error.
* Dialogue state error.
* Bot hỏi lại dữ liệu.
* Hallucination.
* Invalid JSON.
* Exception handling error.
* Latency cao.

Mỗi failure case cần ghi:

* Input.
* Expected behaviour.
* Actual behaviour.
* Nguyên nhân.
* Hướng cải thiện.

### 4.10. Documentation

Người 2 phụ trách chính:

* `docs/architecture.md`
* `docs/dialogue_spec.md`
* `docs/exception_handling.md`
* `docs/evaluation_plan.md`
* `docs/evaluation_report.md`

Nội dung cần có:

* Pipeline design.
* Model choices.
* Dialogue flow.
* State management.
* Exception handling.
* Evaluation methodology.
* Metrics.
* Results.
* Failure analysis.
* Trade-offs.
* Limitations.
* Future improvements.

### Đầu ra Người 2 cần hoàn thành

* Category schema.
* Field schema.
* Prompt templates.
* Dialogue Manager.
* Field collection logic.
* Exception handler.
* Test scenarios.
* Expected outputs.
* Evaluation metrics.
* Evaluation results.
* Architecture document.
* Evaluation report.
* Failure analysis.
* Limitations.

---

# 5. Phần hai người cùng thực hiện

## 5.1. Chốt interface từ đầu

Hai người phải thống nhất input và output của Dialogue Manager.

### Input

```json
{
  "session_id": "call_001",
  "user_text": "Tôi là Nam, xe VF8 bị hết pin tại Cầu Giấy",
  "conversation_history": [],
  "current_state": {}
}
```

### Output mỗi lượt

```json
{
  "response_text": "Dạ anh Nam cho em xin số điện thoại liên hệ ạ.",
  "category": "G_1",
  "fields": {
    "full_name": "Nam",
    "phone": null,
    "vehicle_model": "VF8",
    "current_location": "Cầu Giấy",
    "vehicle_condition": "Hết pin"
  },
  "missing_fields": [
    "phone",
    "license_plate_vin",
    "vehicle_type",
    "current_odo",
    "city_name"
  ],
  "status": "collecting",
  "emergency": false,
  "transfer_to_human": false
}
```

### Final JSON

```json
{
  "category": "G_1",
  "fields": {
    "full_name": "Nguyễn Văn Nam",
    "phone": "0912345678",
    "vehicle_model": "VF8",
    "license_plate_vin": "30A-12345",
    "vehicle_type": "Ô tô điện",
    "current_odo": "25000 km",
    "current_location": "Cầu Giấy",
    "city_name": "Hà Nội",
    "vehicle_condition": "Xe hết pin và không thể di chuyển"
  },
  "post_call": {
    "short_summary": "Khách hàng báo xe VF8 hết pin tại Cầu Giấy và cần hỗ trợ cứu hộ.",
    "sentimental_analysis": "urgent",
    "emergency": "no"
  }
}
```

## 5.2. Review chéo

* Người 1 review khả năng tích hợp của Dialogue Manager.
* Người 2 review hành vi hội thoại của pipeline.
* Người 1 không tự thay đổi schema.
* Người 2 không tự thay đổi interface pipeline.
* Mọi thay đổi phải được thống nhất trước.

## 5.3. Integration test

Cả hai cùng kiểm thử:

```text
Transcript mode
→ Dialogue Manager
→ Response
→ State update
→ Final JSON
```

Sau khi ổn định mới kiểm thử:

```text
Microphone
→ ASR
→ Dialogue Manager
→ Response
→ Final JSON
```

## 5.4. Evaluation

* Người 1 chạy evaluation runner và cung cấp logs.
* Người 2 tính metrics và phân tích lỗi.
* Cả hai review kết quả và sửa lỗi quan trọng.

## 5.5. README và reproducibility

* Người 1 viết phần cài đặt và cách chạy.
* Người 2 viết phần mô tả hệ thống, test và evaluation.
* Cả hai thử chạy từ một môi trường sạch.

## 5.6. Demo

* Người 1 phụ trách vận hành hệ thống và giải thích pipeline.
* Người 2 phụ trách kịch bản hội thoại, exception cases và evaluation.
* Cả hai cùng trình bày trade-offs và limitations.

---

# 6. Bảng phân công tổng hợp

| Hạng mục              | Người 1               | Người 2          |
| --------------------- | --------------------- | ---------------- |
| Repository structure  | Chính                 | Review           |
| Python environment    | Chính                 | Hỗ trợ           |
| Transcript mode       | Chính                 | Test             |
| Audio file input      | Chính                 | Test             |
| Microphone input      | Chính                 | Test             |
| ASR integration       | Chính                 | Test             |
| LLM backend           | Chính                 | Viết prompt      |
| Pipeline integration  | Chính                 | Hỗ trợ           |
| Session và history    | Chính                 | Định nghĩa state |
| Category schema       | Review                | Chính            |
| Field schema          | Review                | Chính            |
| Dialogue Manager      | Tích hợp              | Chính            |
| Intent routing        | Hỗ trợ kỹ thuật       | Chính            |
| Field extraction      | Tích hợp              | Chính            |
| Response generation   | Tích hợp              | Chính            |
| Exception handling    | Tích hợp              | Chính            |
| JSON schema           | Validate              | Định nghĩa       |
| JSON validation       | Chính                 | Review           |
| Evaluation scenarios  | Hỗ trợ                | Chính            |
| Evaluation runner     | Chính                 | Review           |
| Metrics               | Cung cấp logs         | Chính            |
| Latency measurement   | Chính                 | Tổng hợp         |
| Failure analysis      | Cung cấp lỗi          | Chính            |
| Architecture document | Review kỹ thuật       | Chính            |
| Evaluation report     | Cung cấp kết quả      | Chính            |
| README setup          | Chính                 | Review           |
| README usage          | Hỗ trợ                | Chính            |
| CLI và demo           | Chính                 | Chuẩn bị script  |
| TTS                   | Làm nếu còn thời gian | Test             |

---

# 7. Repo structure đề xuất

```text
TaskIntern2506/
├── README.md
├── requirements.txt
├── .env.example
├── configs/
│   ├── model_config.yaml
│   └── dialogue_config.yaml
├── src/
│   └── vinfast_callbot/
│       ├── __init__.py
│       ├── cli.py
│       ├── pipeline.py
│       ├── asr.py
│       ├── llm.py
│       ├── dialogue.py
│       ├── state_manager.py
│       ├── exception_handler.py
│       ├── schemas.py
│       ├── validators.py
│       ├── latency.py
│       └── tts.py
├── evaluation/
│   ├── scenarios.json
│   ├── expected_outputs.json
│   ├── run_evaluation.py
│   ├── metrics.py
│   └── results/
├── docs/
│   ├── architecture.md
│   ├── dialogue_spec.md
│   ├── exception_handling.md
│   ├── evaluation_plan.md
│   └── evaluation_report.md
└── tests/
    ├── test_categories.py
    ├── test_dialogue.py
    ├── test_exceptions.py
    └── test_json_output.py
```

---

# 8. Deliverables cuối dự án

## 8.1. Working bot

* Transcript input.
* Audio hoặc microphone input.
* ASR.
* Dialogue Manager.
* Text response.
* Final JSON.
* TTS nếu có thời gian.

## 8.2. Architecture document

Bao gồm:

* Pipeline.
* Model choices.
* Conversation flow.
* State management.
* Exception handling.
* Design decisions.
* Trade-offs.

## 8.3. Evaluation framework

Bao gồm:

* Test scenarios.
* Expected outputs.
* Automated runner.
* Metrics.
* Exception tests.
* Latency measurement.

## 8.4. Evaluation report

Bao gồm:

* Kết quả metrics.
* Failure cases.
* Latency breakdown.
* Limitations.
* Honest assessment.

## 8.5. Reproducibility

Bao gồm:

* `README.md`
* `requirements.txt`
* `.env.example`
* Hướng dẫn cài đặt.
* Hướng dẫn chạy bot.
* Hướng dẫn chạy evaluation.
* Không chứa credentials.

---

# 9. Thứ tự ưu tiên nếu bị trễ

1. Transcript mode chạy được.
2. Dialogue Manager xử lý đủ 5 category.
3. Thu thập đúng required fields.
4. Final JSON đúng format.
5. Emergency, correction, missing field và hang-up.
6. Evaluation có metrics thật.
7. Latency measurement.
8. README và reports.
9. Audio file và microphone.
10. TTS.

Không làm TTS nếu core bot, exception handling, evaluation hoặc documentation chưa ổn định.

---

# 10. Tiêu chí hoàn thành

Dự án được coi là hoàn thành khi:

* Bot xử lý đủ 5 category.
* Có ít nhất 2 scenarios cho mỗi category.
* Có ít nhất 10 normal scenarios.
* Có test exception cases.
* Có strategy cho đầy đủ 8 exception situations.
* Không hỏi lại field đã xác nhận.
* Khách hàng có thể sửa thông tin.
* Emergency được ưu tiên.
* Hang-up sinh partial JSON với field thiếu là `null`.
* Final JSON hợp lệ.
* Có ít nhất một automated metric.
* Có latency per turn.
* Có failure analysis.
* Có README và `requirements.txt`.
* Có thể chạy lại từ môi trường sạch.
* Không chứa credentials trong source code.
