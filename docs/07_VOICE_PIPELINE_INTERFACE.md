# 07 — Voice Pipeline Interface

## 1. Mục tiêu

Quy định interface giữa voice runtime của Người 1 và dialogue engine của Người 2.

Dialogue engine không phụ thuộc trực tiếp vào microphone, audio library hoặc TTS backend.

## 2. Luồng chính

```text
Microphone
  ↓
VAD
  ↓
ASR partial/final transcript
  ↓
DialogueInput
  ↓
DialogueOutput
  ↓
TTS
```

## 3. Event types

```text
user_utterance
partial_transcript
final_transcript
hangup
timeout
barge_in
system_error
```

Dialogue engine chủ yếu xử lý:

```text
final_transcript
hangup
timeout
system_error
```

Partial transcript có thể dùng cho UI hoặc preview, nhưng không cập nhật field chính thức nếu chưa final.

## 4. Metadata

```json
{
  "asr_confidence": 0.87,
  "is_final_transcript": true,
  "was_interrupted": false,
  "event_type": "final_transcript",
  "audio_duration_ms": 3200
}
```

## 5. Transcript policy

- Chỉ final transcript mới được dùng để cập nhật state.
- Partial transcript không được commit field.
- Empty transcript phải đi vào unclear-input flow.
- ASR confidence thấp ở critical field phải yêu cầu xác nhận.
- Dialogue engine không tự đọc audio.

## 6. Barge-in

Khi bot đang nói và khách cắt ngang:

1. Voice runtime phát hiện speech.
2. TTS phải dừng.
3. Voice runtime gửi turn mới với:

```json
{
  "was_interrupted": true,
  "event_type": "barge_in"
}
```

4. Dialogue engine xử lý transcript mới như một user turn.
5. Phần response TTS chưa phát hết không được coi là đã được khách nghe đầy đủ.

## 7. Turn states ở voice runtime

```text
idle
listening
transcribing
thinking
speaking
interrupted
completed
```

Các trạng thái này không thay thế call status trong dialogue state.

## 8. Hang-up event

Input:

```json
{
  "event_type": "hangup",
  "transcript": "",
  "state": {}
}
```

Expected:

- action `END_PARTIAL_CALL`;
- sinh partial JSON;
- `should_end_call = true`.

## 9. Timeout

Nếu khách im lặng:

- timeout ngắn: nhắc lại nhẹ;
- timeout lặp lại: handoff hoặc kết thúc theo policy;
- không tăng failed turn count quá nhanh chỉ vì khoảng nghỉ tự nhiên.

## 10. Error handling

Nếu ASR lỗi:

```json
{
  "error_code": "ASR_FAILED",
  "recoverable": true
}
```

Dialogue engine có thể trả:

```text
Dạ em chưa nghe rõ, anh/chị vui lòng nói lại giúp em ạ.
```

Nếu system error không recover:

```text
transfer_to_human = true
handoff_reason = system_error
```

## 11. Latency contract

Người 1 cung cấp log:

```json
{
  "session_id": "call-001",
  "turn_id": 3,
  "asr_latency_ms": 420,
  "dialogue_latency_ms": 760,
  "tts_start_latency_ms": 180,
  "total_turn_latency_ms": 1360,
  "barge_in_stop_latency_ms": null
}
```

Người 2 dùng log này cho evaluation report.

## 12. Transcript mode

Pipeline phải hỗ trợ:

```text
text input
→ DialogueInput
→ DialogueOutput
```

Transcript mode không cần microphone, VAD hoặc TTS.

## 13. Contract tests

- final transcript cập nhật state;
- partial transcript không cập nhật state;
- hang-up sinh partial JSON;
- barge-in không làm crash;
- ASR low confidence kích hoạt confirmation;
- empty transcript kích hoạt unclear-input flow.

## 14. ASR hotword integration

Voice pipeline có thể đọc:

```text
resources/asr_hotwords.txt
```

để bias ASR về canonical model names và alias quan trọng.

Metadata có thể bổ sung:

```json
{
  "asr_confidence": 0.78,
  "recognized_vehicle_span": "ép tám",
  "hotword_catalog_version": "1.0"
}
```

Quy tắc:

- hotword chỉ hỗ trợ ASR;
- dialogue layer vẫn phải normalize và validate;
- partial transcript không được commit model;
- model chỉ được cập nhật từ final transcript;
- confidence thấp phải đi qua confirmation policy.
