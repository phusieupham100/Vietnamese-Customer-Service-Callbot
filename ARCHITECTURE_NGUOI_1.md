# Kiến trúc riêng cho Người 1 - Pipeline, ASR, LLM Backend và Demo

## 1. Vai trò của Người 1 trong dự án

Người 1 chịu trách nhiệm xây dựng phần nền tảng để callbot chạy được end-to-end. Nói ngắn gọn, Người 1 biến các module rời rạc thành một hệ thống có thể nhận input, xử lý hội thoại, trả câu trả lời và xuất JSON hợp lệ.

Phạm vi của Người 1 gồm:

- Thiết kế cấu trúc repository và môi trường chạy.
- Xây dựng CLI/demo script.
- Làm transcript mode để test bot không cần audio.
- Tích hợp audio file input.
- Tích hợp microphone input nếu kịp.
- Tích hợp ASR để chuyển audio tiếng Việt thành transcript.
- Tích hợp local LLM backend hoặc module dialogue do Người 2 phát triển.
- Quản lý session và lịch sử hội thoại.
- Điều phối pipeline end-to-end.
- Parse và validate JSON output.
- Ghi log latency.
- Chuẩn bị `requirements.txt`, `.env.example` và README phần cài đặt.
- Tích hợp TTS nếu các phần bắt buộc đã hoàn thành.

Người 1 không phải người quyết định chính về schema nghiệp vụ, required fields, prompt hội thoại, exception strategy và evaluation metrics. Những phần đó do Người 2 phụ trách chính, còn Người 1 đảm bảo chúng được tích hợp ổn định vào pipeline.

## 2. Mục tiêu kỹ thuật

Phần của Người 1 cần đạt các mục tiêu sau:

- Bot chạy được bằng transcript mode trước.
- Pipeline có thể nhận input từ transcript, audio file hoặc microphone.
- ASR lỗi không làm hệ thống crash.
- Dialogue engine hoặc LLM backend được gọi qua một interface rõ ràng.
- Session được giữ qua nhiều lượt nói.
- Output từ dialogue/LLM được parse và validate trước khi cập nhật state.
- Mỗi lượt có log latency.
- Có script demo dễ chạy để phục vụ trình bày cuối.
- Có fallback rõ ràng nếu ASR, microphone hoặc LLM local không ổn định.

## 3. Kiến trúc module của Người 1

```text
CLI / Demo Script
-> Input Adapter
-> ASR Adapter
-> Transcript Normalizer
-> Pipeline Orchestrator
-> Session Manager
-> Dialogue / LLM Integration
-> JSON Parser + Validator
-> Latency Logger
-> Response Output
```

Các module chính:

- `cli.py`: nhận tham số chạy demo và gọi pipeline.
- `input_adapter.py`: chuẩn hóa input từ text, audio file hoặc microphone.
- `asr.py`: chuyển audio thành transcript.
- `pipeline.py`: điều phối toàn bộ luồng xử lý.
- `session.py`: lưu state và history theo session.
- `llm_client.py`: gọi local LLM nếu dùng LLM.
- `validators.py`: parse và validate JSON output.
- `logging_utils.py`: ghi latency và lỗi.
- `tts.py`: optional, phát âm thanh từ `response_text` nếu còn thời gian.

## 4. Cấu trúc thư mục đề xuất cho phần Người 1

```text
src/
  vinfast_callbot/
    __init__.py
    cli.py
    pipeline.py
    input_adapter.py
    asr.py
    llm_client.py
    session.py
    validators.py
    logging_utils.py
    tts.py
requirements.txt
.env.example
README.md
```

Ý nghĩa từng file:

- `cli.py`: entrypoint cho transcript mode, audio file mode, microphone mode.
- `pipeline.py`: nơi nối các bước input, ASR, session, dialogue, validation và logging.
- `input_adapter.py`: nhận input thô và chuyển thành format thống nhất cho pipeline.
- `asr.py`: bọc model ASR, ví dụ Whisper, faster-whisper hoặc PhoWhisper.
- `llm_client.py`: bọc local LLM backend như Ollama, llama.cpp hoặc Hugging Face.
- `session.py`: quản lý session id, turn id, history và state.
- `validators.py`: kiểm tra output có đúng JSON contract không.
- `logging_utils.py`: ghi log latency và lỗi theo từng lượt.
- `tts.py`: module bonus, không thuộc phần bắt buộc ban đầu.

## 5. Luồng chạy end-to-end

Pipeline chính:

```text
1. CLI nhận input từ người dùng.
2. Input Adapter xác định input mode.
3. Nếu input là audio, ASR Adapter chuyển audio thành transcript.
4. Nếu input là text, bỏ qua ASR.
5. Transcript Normalizer làm sạch transcript.
6. Session Manager load session hiện tại.
7. Pipeline gửi transcript + state sang Dialogue Engine hoặc LLM Client.
8. Nhận output dạng JSON.
9. JSON Parser + Validator kiểm tra output.
10. Nếu output hợp lệ, cập nhật session.
11. Latency Logger ghi thời gian xử lý.
12. CLI hiển thị response_text và JSON.
```

Pipeline ở dạng rút gọn:

```text
Transcript / Audio file / Microphone
-> ASR nếu cần
-> Transcript
-> Session state
-> Dialogue / LLM
-> Valid JSON
-> Text response
```

Nguyên tắc quan trọng:

- Transcript mode là đường chạy chính để phát triển và demo an toàn.
- Audio file mode làm sau transcript mode.
- Microphone mode làm sau cùng vì phụ thuộc môi trường máy.
- TTS chỉ làm khi core pipeline, dialogue và evaluation đã ổn.

## 6. Input Adapter

Input Adapter giúp pipeline không phải quan tâm input đến từ đâu.

Output chuẩn của Input Adapter:

```json
{
  "session_id": "demo-001",
  "input_mode": "transcript",
  "text": "Xe tôi bị chết máy trên cao tốc",
  "audio_path": null
}
```

Ba mode cần hỗ trợ:

### 6.1 Transcript mode

Transcript mode dùng để nhập trực tiếp câu nói của khách hàng.

Lệnh demo:

```powershell
python -m vinfast_callbot.cli --transcript "Tôi muốn kiểm tra đơn hàng"
python -m vinfast_callbot.cli --interactive
```

Yêu cầu:

- Chạy được ngay cả khi chưa có ASR.
- Hỗ trợ nhập nhiều lượt trong cùng session.
- Là mode chính cho evaluation.
- Là fallback khi audio demo lỗi.

### 6.2 Audio file mode

Audio file mode dùng để test ASR bằng file có sẵn.

Lệnh demo:

```powershell
python -m vinfast_callbot.cli --audio-file samples\g1_rescue.wav
```

Yêu cầu:

- Nhận đường dẫn file audio.
- Kiểm tra file tồn tại.
- Gọi ASR để sinh transcript.
- In transcript để debug.
- Tiếp tục đưa transcript vào dialogue pipeline.

### 6.3 Microphone mode

Microphone mode dùng cho demo gần với cuộc gọi thật.

Lệnh demo:

```powershell
python -m vinfast_callbot.cli --microphone
```

Yêu cầu:

- Ghi âm từng lượt.
- Lưu tạm audio thành file.
- Gọi ASR để lấy transcript.
- Có phím hoặc lệnh để kết thúc cuộc gọi.
- Nếu microphone lỗi, thông báo rõ và quay về transcript mode.

## 7. ASR Adapter

ASR Adapter chịu trách nhiệm chuyển tiếng nói tiếng Việt thành transcript.

Công nghệ có thể dùng:

- `faster-whisper`.
- Whisper.
- PhoWhisper.
- ASR backend tương đương.

Interface đề xuất:

```python
from dataclasses import dataclass


@dataclass
class ASRResult:
    transcript: str
    latency_ms: float
    confidence: float | None = None
    error: str | None = None


class ASRAdapter:
    def transcribe(self, audio_path: str) -> ASRResult:
        ...
```

Trách nhiệm:

- Load model từ config hoặc biến môi trường.
- Nhận `audio_path`.
- Trả transcript tiếng Việt.
- Ghi latency ASR.
- Bắt lỗi file audio, lỗi model, lỗi device.
- Không để lỗi ASR làm crash pipeline.

Fallback khi ASR lỗi:

```json
{
  "transcript": "",
  "latency_ms": 0,
  "confidence": null,
  "error": "ASR failed to transcribe audio"
}
```

Pipeline sẽ chuyển transcript rỗng thành trạng thái input không rõ để dialogue engine hỏi lại khách hàng.

## 8. Transcript Normalizer

Transcript Normalizer chuẩn hóa text trước khi gửi vào dialogue.

Xử lý tối thiểu:

- Xóa khoảng trắng đầu/cuối.
- Gộp nhiều khoảng trắng liên tiếp.
- Giữ nguyên tiếng Việt có dấu.
- Không tự sửa nội dung nghiệp vụ.
- Kiểm tra transcript rỗng.
- Đánh dấu transcript không rõ nếu quá ngắn hoặc ASR trả lỗi.

Ví dụ:

```text
"   xe   tôi   chết máy   "
-> "xe tôi chết máy"
```

## 9. Pipeline Orchestrator

`pipeline.py` là trung tâm điều phối.

Input của pipeline:

```json
{
  "session_id": "demo-001",
  "input_mode": "transcript",
  "text": "Xe tôi bị chết máy trên cao tốc",
  "audio_path": null
}
```

Output của pipeline:

```json
{
  "response_text": "Dạ anh/chị đang ở vị trí nào để em hỗ trợ cứu hộ ạ?",
  "json": {
    "category": "G_1",
    "fields": {
      "issue": "xe chết máy",
      "location": null
    },
    "missing_fields": [
      "location",
      "phone"
    ],
    "status": "collecting",
    "transfer_to_human": false,
    "emergency": true
  },
  "latency": {
    "asr_latency_ms": 0,
    "dialogue_latency_ms": 640,
    "validation_latency_ms": 4,
    "total_latency_ms": 660
  }
}
```

Pipeline cần đảm bảo:

- Không gọi ASR nếu input đã là transcript.
- Không gọi dialogue nếu input hoàn toàn rỗng mà chưa được đánh dấu.
- Luôn trả response có cấu trúc cho CLI.
- Luôn ghi log lỗi nếu có exception.
- Không ghi đè session bằng JSON không hợp lệ.

## 10. Session Manager

Session Manager lưu trạng thái qua nhiều lượt hội thoại.

State tối thiểu:

```json
{
  "session_id": "demo-001",
  "turn_id": 3,
  "category": "G_1",
  "fields": {
    "issue": "xe chết máy"
  },
  "missing_fields": [
    "location",
    "phone"
  ],
  "status": "collecting",
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
  "unclear_turns": 0
}
```

Session Manager cần có các thao tác:

- Tạo session mới.
- Load session theo `session_id`.
- Append user transcript.
- Append bot response.
- Update category, fields, missing fields và status.
- Reset session khi bắt đầu scenario evaluation mới.

Trong demo đơn giản, session có thể lưu in-memory. Nếu cần review sau demo, có thể ghi session ra JSON log.

## 11. Dialogue / LLM Integration

Người 1 tích hợp dialogue engine của Người 2 hoặc local LLM backend qua một interface ổn định.

Input gửi sang dialogue:

```json
{
  "session_id": "demo-001",
  "turn_id": 3,
  "transcript": "Xe tôi bị chết máy trên cao tốc",
  "history": [],
  "state": {
    "category": null,
    "fields": {},
    "missing_fields": [],
    "status": "collecting"
  }
}
```

Output nhận về:

```json
{
  "response_text": "Dạ anh/chị đang ở vị trí nào để em hỗ trợ cứu hộ ạ?",
  "category": "G_1",
  "fields": {
    "issue": "xe chết máy",
    "location": null
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

Nếu dùng local LLM, `llm_client.py` cần xử lý:

- Model endpoint.
- Timeout.
- Request body.
- Prompt input.
- Raw text response.
- Parse JSON.
- Retry hoặc fallback nếu LLM trả output hỏng.

Nếu dùng dialogue rule-based, pipeline vẫn gọi qua cùng một interface để không phải đổi phần còn lại của hệ thống.

## 12. JSON Parser và Validator

Người 1 cần validate mọi output từ dialogue/LLM trước khi cập nhật session.

Các trường bắt buộc ở output từng lượt:

- `response_text`
- `category`
- `fields`
- `missing_fields`
- `status`
- `transfer_to_human`
- `emergency`

Luật validate:

- `response_text` là string.
- `category` thuộc `G_1`, `G_2`, `G_3`, `G_4`, `G_5` hoặc `null`.
- `fields` là object.
- `missing_fields` là list.
- `status` là string trong tập đã thống nhất.
- `transfer_to_human` là boolean.
- `emergency` là boolean.

Khi output không hợp lệ:

- Không update session bằng output lỗi.
- Ghi log lỗi validate.
- Trả fallback response.
- Nếu dùng LLM, có thể gọi lại một lần để sửa JSON.

Fallback response đề xuất:

```json
{
  "response_text": "Dạ hệ thống chưa xử lý được thông tin vừa rồi, anh/chị vui lòng nói lại giúp em ạ.",
  "category": null,
  "fields": {},
  "missing_fields": [],
  "status": "error",
  "transfer_to_human": false,
  "emergency": false
}
```

## 13. Latency Logger

Người 1 cần log latency cho từng lượt.

Các trường log:

- `session_id`
- `turn_id`
- `input_mode`
- `asr_latency_ms`
- `dialogue_latency_ms`
- `validation_latency_ms`
- `total_latency_ms`
- `category`
- `status`
- `error_type`

Ví dụ:

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

Log này phục vụ:

- Debug hệ thống.
- Demo trade-off giữa transcript mode và audio mode.
- Evaluation report.
- Phân tích lỗi nếu pipeline bị chậm hoặc fail.

## 14. Lỗi và fallback cần xử lý

Người 1 cần xử lý các lỗi kỹ thuật sau:

- File audio không tồn tại.
- Audio format không đọc được.
- ASR load model lỗi.
- ASR trả transcript rỗng.
- Microphone không hoạt động.
- Local LLM backend không chạy.
- LLM timeout.
- LLM trả JSON sai format.
- Dialogue engine raise exception.
- Validator fail.
- Session id không tồn tại.

Chiến lược:

- Không để lỗi kỹ thuật làm crash CLI.
- Ghi lỗi vào log.
- Trả response fallback thân thiện.
- Giữ session cũ nếu output mới không hợp lệ.
- Luôn giữ transcript mode làm đường demo an toàn.

## 15. Tích hợp với evaluation

Người 1 hỗ trợ evaluation bằng cách để `evaluation/run_evaluation.py` gọi được pipeline qua transcript mode.

Luồng evaluation:

```text
Load scenario
-> Reset session
-> Gửi từng user turn vào pipeline transcript mode
-> Nhận response + JSON
-> Ghi latency
-> Trả kết quả cho evaluator
```

Người 1 cần đảm bảo:

- Pipeline có thể chạy nhiều scenario liên tiếp.
- Có cách reset session.
- Output luôn là JSON parse được.
- Latency được trả hoặc ghi log để Người 2 tổng hợp.

## 16. Demo script của Người 1

Các lệnh demo cần chuẩn bị:

```powershell
python -m vinfast_callbot.cli --interactive
python -m vinfast_callbot.cli --transcript "Xe tôi bị chết máy trên cao tốc"
python -m vinfast_callbot.cli --audio-file samples\g1_rescue.wav
python -m vinfast_callbot.cli --microphone
python evaluation\run_evaluation.py
```

Thứ tự demo khuyến nghị:

1. Chạy transcript mode để chứng minh core bot.
2. Chạy một case nhiều lượt để chứng minh session.
3. Chạy audio file để chứng minh ASR.
4. Chạy evaluation để chứng minh có metrics.
5. Chạy microphone nếu môi trường ổn định.

## 17. README và cấu hình

Người 1 phụ trách README phần cài đặt và vận hành.

README cần có:

- Python version.
- Cách tạo môi trường ảo.
- Cách cài `requirements.txt`.
- Cách cấu hình `.env`.
- Cách chọn ASR model.
- Cách chạy transcript demo.
- Cách chạy audio demo.
- Cách chạy evaluation.
- Các lỗi thường gặp.

`.env.example` nên có:

```text
ASR_MODEL_NAME=
ASR_DEVICE=
LLM_BACKEND=
LLM_MODEL_NAME=
LLM_BASE_URL=
LOG_LEVEL=
```

Không để API key, token hoặc credential thật trong repo.

## 18. TTS optional

TTS chỉ làm nếu còn thời gian.

Vị trí trong pipeline:

```text
response_text
-> TTS
-> audio response
```

Nguyên tắc:

- TTS không thay đổi JSON.
- TTS không thay đổi state.
- Nếu TTS lỗi, vẫn in `response_text`.
- Không ưu tiên TTS hơn transcript mode, dialogue, exception handling và evaluation.

## 19. Checklist bàn giao của Người 1

Người 1 cần bàn giao:

- CLI chạy được.
- Transcript mode chạy end-to-end.
- Audio file mode có ASR hoặc fallback rõ ràng.
- Microphone mode nếu kịp.
- ASR Adapter.
- Local LLM Client hoặc integration layer.
- Pipeline Orchestrator.
- Session Manager.
- JSON Parser và Validator.
- Latency Logger.
- Demo commands.
- README phần cài đặt và chạy.
- `requirements.txt`.
- `.env.example`.

## 20. Tiêu chí hoàn thành phần Người 1

Phần Người 1 được xem là hoàn thành khi:

- `--interactive` chạy được nhiều lượt.
- `--transcript` chạy được một câu input.
- Audio file có thể đi qua ASR hoặc có fallback transcript rõ ràng.
- Pipeline tích hợp được dialogue engine của Người 2.
- Output mỗi lượt có `response_text` và JSON hợp lệ.
- Session giữ được state qua nhiều lượt.
- Validator chặn output sai format.
- Có latency log cho từng lượt.
- Evaluation runner có thể gọi pipeline bằng transcript mode.
- README đủ để người khác cài và chạy lại.

