# Kiến trúc tổng thể dự án Vietnamese Customer Service Callbot

## 1. Mục tiêu hệ thống

Dự án xây dựng một Vietnamese Customer Service Callbot cho bối cảnh chăm sóc khách hàng VinFast. Bot nhận đầu vào bằng transcript tiếng Việt hoặc giọng nói, hiểu nhu cầu của khách hàng, phân loại cuộc gọi vào đúng nhóm nghiệp vụ, thu thập các thông tin còn thiếu qua hội thoại tự nhiên và sinh kết quả cuối ở dạng JSON có thể kiểm tra tự động.

Mục tiêu chính:

- Nhận input từ transcript, audio file hoặc microphone.
- Dùng ASR để chuyển giọng nói tiếng Việt thành transcript.
- Phân loại cuộc gọi vào 5 nhóm nghiệp vụ `G_1` đến `G_5`.
- Thu thập required fields theo từng nhóm.
- Không hỏi lại thông tin đã có.
- Cho phép khách hàng sửa thông tin trong quá trình hội thoại.
- Xử lý các trường hợp ngoại lệ như input không rõ, intent mơ hồ, emergency hoặc khách kết thúc giữa chừng.
- Sinh `response_text` cho từng lượt và final JSON cuối cuộc gọi.
- Có evaluation framework để đo chất lượng bot bằng kịch bản kiểm thử.
- Có log latency để đánh giá tốc độ xử lý.

TTS là phần bonus. Hệ thống chỉ tích hợp TTS sau khi transcript mode, dialogue, JSON, exception handling, evaluation và tài liệu đã ổn định.

## 2. Kiến trúc mức cao

Luồng xử lý tổng thể:

```text
Transcript / Audio file / Microphone
-> Input Adapter
-> ASR Adapter
-> Transcript Normalizer
-> Session Manager
-> Dialogue Manager / LLM Backend
-> Category + Field Extraction + Exception Handling
-> JSON Parser + Validator
-> Response Renderer
-> Logger + Evaluation Output
```

Với transcript mode, pipeline bỏ qua ASR:

```text
Transcript
-> Transcript Normalizer
-> Session Manager
-> Dialogue Manager
-> JSON Validator
-> Text Response + Updated State
```

Với audio mode, pipeline đi qua ASR trước:

```text
Audio file / Microphone
-> ASR
-> Transcript
-> Transcript Normalizer
-> Dialogue Manager
-> JSON Validator
-> Text Response + Updated State
```

Nguyên tắc thiết kế quan trọng là transcript mode phải chạy ổn định trước. ASR và microphone là lớp input bổ sung, không được làm hỏng khả năng demo bằng text.

## 3. Cấu trúc repository đề xuất

```text
Vietnamese-Customer-Service-Callbot/
  README.md
  requirements.txt
  .env.example
  ARCHITECTURE.md
  src/
    vinfast_callbot/
      __init__.py
      cli.py
      pipeline.py
      input_adapter.py
      asr.py
      llm_client.py
      dialogue.py
      schemas.py
      session.py
      validators.py
      logging_utils.py
      tts.py
  evaluation/
    scenarios.json
    run_evaluation.py
    results.json
  docs/
    evaluation_report.md
    dialogue_specification.md
    exception_handling.md
  tests/
    test_dialogue.py
    test_validators.py
```

Vai trò chính:

- `cli.py`: điểm chạy demo và test thủ công.
- `pipeline.py`: điều phối toàn bộ luồng xử lý.
- `input_adapter.py`: chuẩn hóa input từ text, audio file hoặc microphone.
- `asr.py`: tích hợp ASR như Whisper, faster-whisper, PhoWhisper hoặc backend tương đương.
- `llm_client.py`: gọi local LLM qua Ollama, llama.cpp, Hugging Face hoặc backend tương đương nếu dùng LLM.
- `dialogue.py`: xử lý phân loại intent, thu thập field, cập nhật state và sinh response.
- `schemas.py`: định nghĩa 5 category, required fields, optional fields và output schema.
- `session.py`: lưu session, history và state cuộc gọi.
- `validators.py`: parse và validate JSON output.
- `logging_utils.py`: ghi latency và lỗi.
- `tts.py`: phát giọng nói từ `response_text` nếu còn thời gian.
- `evaluation/`: chứa kịch bản test, runner và kết quả đánh giá.

## 4. Các nhóm nghiệp vụ

Hệ thống phân loại cuộc gọi vào 5 nhóm:

```text
G_1: Cứu hộ
G_2: Bảo hành và sửa chữa
G_3: Đơn hàng
G_4: Xe máy - Bảo hành
G_5: Hỗ trợ kỹ thuật từ xa
```

Mỗi nhóm có:

- Tên category.
- Required fields.
- Optional fields.
- Câu hỏi dùng để thu thập từng field.
- Điều kiện hoàn tất cuộc gọi.
- Luật xử lý khi thiếu thông tin.
- Luật xử lý khi khách sửa thông tin.

Chi tiết field không nên hard-code rải rác trong nhiều module. Nên tập trung trong `schemas.py` để dialogue manager, validator và evaluation cùng dùng một nguồn sự thật.

## 5. Data contract giữa các module

### 5.1 Input cho dialogue

Sau khi đã có transcript, pipeline gửi vào dialogue manager object có cấu trúc:

```json
{
  "session_id": "demo-001",
  "turn_id": 3,
  "transcript": "Xe tôi bị chết máy trên cao tốc",
  "input_mode": "transcript",
  "history": [
    {
      "role": "user",
      "content": "Tôi cần cứu hộ"
    },
    {
      "role": "assistant",
      "content": "Dạ anh/chị cho em xin vị trí hiện tại ạ."
    }
  ],
  "state": {
    "category": "G_1",
    "fields": {
      "issue": "xe chết máy"
    },
    "missing_fields": [
      "location",
      "phone"
    ],
    "status": "collecting"
  }
}
```

### 5.2 Output từng lượt

Dialogue manager hoặc LLM backend trả về output từng lượt:

```json
{
  "response_text": "Dạ anh/chị đang ở vị trí nào để em hỗ trợ cứu hộ ạ?",
  "category": "G_1",
  "fields": {
    "issue": "xe chết máy",
    "location": null,
    "phone": null
  },
  "missing_fields": [
    "location",
    "phone"
  ],
  "status": "collecting",
  "transfer_to_human": false,
  "emergency": true
}
```

### 5.3 Final JSON cuối cuộc gọi

Khi cuộc gọi hoàn tất hoặc khách kết thúc giữa chừng, hệ thống sinh final JSON:

```json
{
  "category": "G_1",
  "fields": {
    "issue": "xe chết máy",
    "location": "cao tốc Hà Nội - Hải Phòng",
    "phone": "0900000000"
  },
  "post_call": {
    "short_summary": "Khách cần cứu hộ do xe chết máy trên cao tốc.",
    "sentimental_analysis": "lo lắng",
    "emergency": "yes"
  },
  "status": "completed",
  "transfer_to_human": false
}
```

Nếu khách kết thúc giữa chừng, các field chưa có giữ giá trị `null`, `status` chuyển sang trạng thái phù hợp như `ended` hoặc `partial`.

## 6. Input Adapter và ASR

Input layer hỗ trợ ba chế độ.

### Transcript mode

Transcript mode là đường chạy chính để phát triển, test và evaluation.

Yêu cầu:

- Nhận một câu transcript qua CLI.
- Hỗ trợ interactive mode nhiều lượt.
- Không phụ thuộc microphone, audio driver hoặc ASR model.
- Là fallback chính khi audio demo lỗi.

Lệnh demo:

```powershell
python -m vinfast_callbot.cli --transcript "Tôi muốn kiểm tra đơn hàng"
python -m vinfast_callbot.cli --interactive
```

### Audio file mode

Audio file mode dùng để kiểm thử ASR có kiểm soát.

Yêu cầu:

- Nhận đường dẫn file audio.
- Gọi ASR để lấy transcript.
- Hiển thị transcript trước khi đưa vào dialogue để dễ debug.
- Ghi latency ASR.
- Nếu ASR thất bại, trả lỗi có cấu trúc thay vì crash.

### Microphone mode

Microphone mode phục vụ demo gần với cuộc gọi thật.

Yêu cầu:

- Ghi âm từng lượt nói.
- Chuyển audio sang ASR.
- Gửi transcript vào pipeline.
- Có cách thoát cuộc gọi rõ ràng.
- Không được thay thế transcript mode trong evaluation chính.

## 7. Dialogue Manager

Dialogue Manager là lõi điều khiển hội thoại. Module này có thể dùng rule-based logic, local LLM hoặc kết hợp cả hai.

Trách nhiệm:

- Phân loại category.
- Trích xuất field từ transcript.
- Cập nhật state sau mỗi lượt.
- Xác định field còn thiếu.
- Chỉ hỏi field còn thiếu.
- Không hỏi lại thông tin đã có.
- Cho phép khách sửa thông tin đã cung cấp.
- Thu thập nhiều field trong một lượt nói nếu có thể.
- Xác định khi nào cuộc gọi đủ thông tin để hoàn tất.
- Sinh `response_text` tự nhiên, lịch sự và đúng phạm vi.
- Sinh final JSON khi cuộc gọi kết thúc.

Luồng logic:

```text
Transcript mới
-> Detect category hoặc dùng category hiện có
-> Extract fields
-> Detect correction / exception
-> Merge fields vào state
-> Tính missing_fields
-> Nếu đủ required fields: finalize
-> Nếu thiếu field: hỏi field tiếp theo
-> Trả response_text + state mới
```

## 8. Local LLM Backend

Nếu dùng LLM, backend nên chạy local để phù hợp scope dự án.

Lựa chọn có thể dùng:

- Ollama.
- llama.cpp.
- Hugging Face local pipeline.
- Backend tương đương.

LLM không nên được gọi trực tiếp từ nhiều nơi. Nên bọc qua `llm_client.py` để:

- Quản lý endpoint và model config.
- Gửi prompt theo format thống nhất.
- Ép output JSON.
- Cài timeout.
- Bắt lỗi kết nối.
- Retry nhẹ khi lỗi tạm thời.
- Trả fallback nếu output không parse được.

Nếu dùng rule-based dialogue, `llm_client.py` có thể không bắt buộc. Khi đó `dialogue.py` vẫn phải trả output đúng schema để pipeline không đổi.

## 9. Session Manager

Session Manager lưu toàn bộ trạng thái cuộc gọi.

Thông tin cần có:

- `session_id`.
- `turn_id`.
- Lịch sử transcript của khách.
- Lịch sử response của bot.
- Category hiện tại.
- Fields đã thu thập.
- Missing fields.
- Trạng thái cuộc gọi.
- Số lượt input không rõ.
- Cờ `emergency`.
- Cờ `transfer_to_human`.

State nên được cập nhật sau khi output đã validate thành công. Nếu JSON lỗi, session không nên bị ghi đè bằng dữ liệu hỏng.

## 10. Exception Handling

Hệ thống cần xử lý 8 nhóm exception:

- Thiếu thông tin.
- Khách sửa thông tin.
- Intent mơ hồ.
- Câu hỏi ngoài phạm vi.
- Input không rõ hoặc ASR transcript rỗng.
- Emergency.
- Bot không hiểu sau nhiều lượt.
- Khách kết thúc giữa cuộc gọi.

Chiến lược chung:

- Với thiếu thông tin: hỏi đúng field còn thiếu.
- Với correction: cập nhật field cũ bằng thông tin mới, không giữ cả hai giá trị mâu thuẫn.
- Với intent mơ hồ: hỏi lại để phân loại, không đoán bừa.
- Với out-of-scope: lịch sự báo phạm vi hỗ trợ và kéo về các nhóm nghiệp vụ liên quan.
- Với input không rõ: xin khách nhắc lại, đồng thời tăng bộ đếm unclear turn.
- Với emergency: ưu tiên an toàn, route về `G_1`, có thể chuyển người thật nếu cần.
- Với nhiều lượt không hiểu: đề xuất chuyển nhân viên hỗ trợ.
- Với hang-up: sinh partial JSON với field thiếu là `null`.

## 11. JSON Parser và Validator

Validator là lớp bảo vệ giữa dialogue/LLM và pipeline.

Validator kiểm tra:

- Output parse được thành JSON.
- Có `response_text` khi đang hội thoại.
- `category` hợp lệ hoặc `null` khi chưa xác định.
- `fields` là object.
- `missing_fields` là list.
- `status` thuộc tập trạng thái cho phép.
- `transfer_to_human` là boolean.
- `emergency` là boolean.
- Final JSON có `category`, `fields` và `post_call` khi cuộc gọi kết thúc.

Khi validate thất bại:

- Ghi log lỗi.
- Không cập nhật session bằng output lỗi.
- Trả fallback response cho khách.
- Nếu dùng LLM, có thể gọi lại với prompt sửa JSON.

## 12. Logging và latency

Mỗi lượt hội thoại cần log các thông tin:

```json
{
  "session_id": "demo-001",
  "turn_id": 2,
  "input_mode": "audio_file",
  "asr_latency_ms": 1210,
  "dialogue_latency_ms": 640,
  "validation_latency_ms": 5,
  "total_latency_ms": 1855,
  "category": "G_1",
  "status": "collecting",
  "error_type": null
}
```

Latency được dùng cho:

- Debug hiệu năng.
- Evaluation report.
- Demo trade-off giữa transcript mode và audio mode.
- Xác định bottleneck ASR hoặc LLM.

## 13. Evaluation Framework

Evaluation framework kiểm thử bot bằng nhiều scenario cố định.

Input:

- `evaluation/scenarios.json`
- Mỗi scenario gồm category kỳ vọng, các lượt khách nói, field kỳ vọng và exception kỳ vọng nếu có.

Runner:

```text
Load scenarios
-> Reset session cho từng scenario
-> Chạy từng turn qua transcript mode
-> Thu output JSON
-> So sánh với expected result
-> Tính metrics
-> Ghi results.json
```

Metrics cần có:

- Category accuracy.
- Field extraction accuracy.
- Required-field completion rate.
- JSON validity rate.
- Dialogue success rate.
- Exception handling success rate.
- No-reask rate.
- Latency trung bình mỗi lượt.

Bộ test tối thiểu:

- Ít nhất 10 normal scenarios.
- Mỗi category ít nhất 2 scenarios.
- Ít nhất 3 exception scenarios.
- Nên có thêm case emergency, correction và hang-up.

Evaluation phải dùng số liệu thật từ `results.json`, không tự ước lượng metric trong report.

## 14. Demo flow

Demo nên đi từ đơn giản đến đầy đủ.

### Demo 1: Transcript mode

```powershell
python -m vinfast_callbot.cli --interactive
```

Mục tiêu:

- Chứng minh core dialogue chạy được.
- Bot giữ state qua nhiều lượt.
- Output JSON hợp lệ.

### Demo 2: Audio file mode

```powershell
python -m vinfast_callbot.cli --audio-file samples\g1_rescue.wav
```

Mục tiêu:

- Chứng minh ASR nối được vào pipeline.
- Có transcript và latency ASR.

### Demo 3: Evaluation

```powershell
python evaluation\run_evaluation.py
```

Mục tiêu:

- Chạy nhiều scenario tự động.
- Sinh `evaluation/results.json`.
- Có số liệu phục vụ report.

### Demo 4: Microphone mode

```powershell
python -m vinfast_callbot.cli --microphone
```

Mục tiêu:

- Demo trải nghiệm gần với cuộc gọi thật nếu môi trường âm thanh ổn định.

## 15. Phân chia trách nhiệm

### Người 1

Phụ trách phần bot chạy được:

- Repository structure.
- Môi trường chạy.
- CLI/demo script.
- Transcript mode.
- Audio file input.
- Microphone input.
- ASR adapter.
- Local LLM client hoặc integration layer.
- Pipeline end-to-end.
- Session manager.
- JSON parser và validator.
- Latency logger.
- README phần setup và cách chạy.

### Người 2

Phụ trách logic hội thoại và đánh giá:

- Category schema.
- Required fields và optional fields.
- Prompt templates nếu dùng LLM.
- Dialogue manager.
- Field collection logic.
- Exception handling.
- Test scenarios.
- Evaluation metrics.
- Evaluation report.
- Architecture/documentation phần dialogue, exception và trade-off.

### Cả hai cùng review

- JSON schema cuối cuộc gọi.
- Interface giữa pipeline và dialogue.
- Demo script cuối.
- Evaluation results.
- README.
- Quyết định có làm TTS hay không.

## 16. Thứ tự triển khai ưu tiên

Thứ tự ưu tiên kỹ thuật:

1. Transcript mode chạy end-to-end.
2. Dialogue xử lý đủ 5 category.
3. Required fields được thu thập đúng.
4. Output JSON hợp lệ.
5. Exception handling cho các case quan trọng.
6. Evaluation runner và metrics.
7. ASR audio file.
8. Microphone mode.
9. README, report và reproducibility.
10. TTS nếu còn thời gian.

Không nên ưu tiên giao diện hoặc TTS trước khi dialogue, exception handling và evaluation ổn định.

## 17. Tiêu chí hoàn thành

Dự án được xem là hoàn thành khi:

- Bot chạy được transcript mode end-to-end.
- Có đường ASR cho audio file hoặc microphone, hoặc ghi rõ fallback nếu ASR chưa ổn.
- Bot xử lý đủ 5 category.
- Final JSON đúng schema.
- Các field chưa có trong partial call được giữ là `null`.
- Có xử lý các exception chính.
- Có automated evaluation.
- Có `results.json` với metrics thật.
- Có latency per turn.
- Có README để người khác cài và chạy lại.
- Không có API key hoặc credential trong code.
- Có tài liệu kiến trúc, evaluation report và limitations rõ ràng.

