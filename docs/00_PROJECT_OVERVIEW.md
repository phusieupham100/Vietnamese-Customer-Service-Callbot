# 00 — Project Overview

## 1. Mục tiêu

Xây dựng Vietnamese Customer Service Callbot cho VinFast có thể:

- Nhận giọng nói tiếng Việt từ microphone.
- Chuyển giọng nói thành transcript.
- Quản lý hội thoại bằng local LLM và logic backend.
- Phân loại cuộc gọi vào đúng một trong năm nhóm nghiệp vụ.
- Thu thập đúng các field theo brief.
- Xử lý correction, ambiguous intent, emergency và các exception khác.
- Sinh text response ở mỗi lượt.
- Sinh final JSON cuối cuộc gọi.
- Có evaluation framework và latency report.
- Hỗ trợ TTS và barge-in để gần với callbot thực tế.

## 2. Năm nhóm nghiệp vụ

```text
G_1: Cứu hộ
G_2: Bảo hành và sửa chữa
G_3: Đơn hàng
G_4: Xe máy – Bảo hành
G_5: Hỗ trợ kỹ thuật từ xa
```

## 3. Nguyên tắc sản phẩm

### 3.1 Không phân loại theo triệu chứng đơn thuần

```text
"Xe tôi không khởi động được"
```

chưa đủ để kết luận khách cần cứu hộ.

Bot phải tách:

```text
Tình trạng xe
≠
Nhu cầu dịch vụ
```

### 3.2 Hỏi làm rõ có mục tiêu

Nếu chưa rõ intent, bot chỉ hỏi đúng tín hiệu còn thiếu.

Ví dụ:

```text
Dạ anh/chị có cần hỗ trợ cứu hộ ngay không ạ?
```

Không hỏi khách chọn giữa cả năm nhóm.

### 3.3 Backend kiểm soát state

LLM không được tự quyết định toàn bộ flow. State, field validation, missing fields, next action và finalization phải do backend kiểm soát.

### 3.4 Transcript mode luôn phải tồn tại

Voice pipeline có thể gặp lỗi môi trường. Transcript mode là fallback bắt buộc cho:

- automated evaluation;
- unit test;
- demo khi microphone hoặc ASR gặp lỗi.

## 4. Kiến trúc tổng thể

```text
Microphone
    ↓
Audio Stream
    ↓
VAD / Turn Manager
    ↓
Streaming hoặc Chunk ASR
    ↓
Transcript
    ↓
Vehicle Model Recognition
    ├── Vehicle Catalog
    ├── Vehicle Normalizer
    └── Vehicle Matcher
    ↓
Dialogue Engine
    ├── Signal Extractor
    ├── Emergency Detector
    ├── Intent Router
    ├── Field Extractor
    ├── Validator
    ├── State Updater
    ├── Action Policy
    ├── Exception Handler
    └── Response Generator
    ↓
Text Response
    ├── TTS → Speaker
    └── Per-turn JSON
    ↓
Post-call JSON
```

## 5. Phân chia trách nhiệm

### Người 1 — Voice pipeline và integration

- Microphone stream
- VAD
- Streaming hoặc chunk ASR
- Local LLM client
- TTS
- Barge-in
- Runtime session
- Latency logging
- CLI và voice app
- Technical setup

### Người 2 — Dialogue intelligence và evaluation

- Category schema
- Intent routing
- Field extraction
- Validators
- State update
- Dialogue action policy
- Exception handling
- Response generation
- Post-call JSON
- Evaluation scenarios
- Metrics và report

## 6. Luồng xử lý của Người 2

```text
Transcript + State + History
        ↓
Signal Extractor
        ↓
Correction Detector
        ↓
Emergency Detector
        ↓
Intent Router
        ↓
Field Extractor
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
```

## 7. Scope bắt buộc

- Đủ năm category.
- Field đúng brief.
- Final JSON hợp lệ.
- Tám exception cases.
- At least two scenarios per category.
- Automated metric.
- Failure analysis.
- End-to-end latency per turn.
- Transcript mode.
- Microphone input và ASR.

## 8. Scope nâng cao để giống callbot thực tế

- Partial ASR transcript.
- TTS.
- Turn-taking.
- Barge-in.
- Bot dừng nói khi khách cắt ngang.
- Human handoff reason.
- Critical-field confirmation.

## 9. Ngoài phạm vi 7 ngày

- Tổng đài SIP/PSTN thật.
- Multi-tenant production deployment.
- Fine-tune model.
- CRM thật.
- Policy database production.
- Brand voice TTS.
- Auto dispatch cứu hộ thật.

## 10. Sơ đồ tài liệu

```text
Overview
  ├── Shared Contracts
  ├── Category Schemas
  ├── Intent Routing
  ├── Dialogue State & Policy
  ├── Exception Handling
  ├── Evaluation Spec
  ├── Voice Pipeline Interface
  ├── Implementation Plan
  └── Codex Execution Guide
```

## 11. Vehicle model recognition

Hệ thống phải chuẩn hóa model xe trước khi dùng làm field hoặc routing signal.

```text
Transcript
→ Vehicle Mention Extractor
→ Vehicle Normalizer
→ Vehicle Matcher
→ Vehicle type signal
→ Intent Router
```

Nguyên tắc:

- model xác định loại phương tiện;
- model không tự xác định nhu cầu dịch vụ;
- model mơ hồ phải xác nhận;
- model ngoài catalog không được tự map sang model gần nhất;
- final JSON chỉ lưu canonical model name hoặc raw value đã được khách xác nhận.
