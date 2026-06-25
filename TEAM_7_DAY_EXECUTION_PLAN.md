# Team 7-Day Execution Plan From Scratch

## Mục Tiêu
Trong 7 ngày, nhóm 2 người xây dựng một Vietnamese Customer Service Callbot cho VinFast theo Task 3:
- Nhận đầu vào giọng nói hoặc transcript tiếng Việt.
- ASR chuyển audio thành transcript.
- Dialogue/LLM phân loại cuộc gọi vào 5 nhóm `G_1` đến `G_5`.
- Thu thập đủ required fields qua hội thoại tự nhiên.
- Sinh text response và final JSON cuối cuộc gọi.
- Xử lý exception cases.
- Có evaluation framework, report, README và `requirements.txt`.

TTS là bonus. Chỉ làm TTS nếu core bot, evaluation và docs đã ổn.

## Chia Vai Trò Từ Đầu

### Người 1: Pipeline, ASR, LLM Backend, Demo
Phụ trách chính phần bot chạy được:
- Thiết kế repo structure.
- Tích hợp ASR: Whisper, faster-whisper, PhoWhisper hoặc model tương đương.
- Làm input modes: transcript mode trước, audio file/microphone sau.
- Tích hợp LLM backend hoặc dialogue engine.
- Kết nối pipeline: input -> ASR/transcript -> dialogue -> response -> JSON.
- Đảm bảo có CLI/app demo dễ chạy.
- Quản lý `requirements.txt`, `.env.example`, setup instructions.

### Người 2: Dialogue Design, Schema, Evaluation, Documents
Phụ trách chính phần logic và đánh giá:
- Đọc brief, tóm tắt yêu cầu.
- Định nghĩa 5 category và field schema.
- Thiết kế conversation flow cho từng category.
- Thiết kế strategy cho 8 exception cases.
- Viết test scenarios, rubrics, metrics.
- Viết architecture document và evaluation report.
- Chạy evaluation, phân tích failure cases.

### Phần Cả Hai Cùng Review
- JSON schema cuối cuộc gọi.
- Demo script cuối.
- Evaluation results.
- README và reproducibility.
- Quyết định có làm TTS hay không.

## Repo Structure Đề Xuất
```text
TaskIntern2506/
  README.md
  requirements.txt
  .env.example
  src/
    vinfast_callbot/
      __init__.py
      cli.py
      asr.py
      llm.py
      dialogue.py
      schemas.py
      tts.py
  evaluation/
    scenarios.json
    run_evaluation.py
    results.json
  docs/
    architecture.md
    evaluation_report.md
  tests/
    test_dialogue.py
```

## Ngày 1: Đọc Brief, Chốt Scope, Chốt Tech Stack

Mục tiêu:
- Cả hai hiểu rõ task.
- Chốt cách làm tối thiểu nhưng chắc chắn trong 7 ngày.

Người 1 làm:
- Tạo repo structure.
- Tạo môi trường Python.
- Thử nhanh các lựa chọn ASR:
  - `faster-whisper`
  - Whisper/PhoWhisper nếu máy đủ mạnh
  - transcript mode làm fallback
- Đề xuất cách chạy demo: CLI là lựa chọn nhanh nhất.

Người 2 làm:
- Tóm tắt brief thành checklist.
- Liệt kê 5 categories và required fields:
  - `G_1`: cứu hộ
  - `G_2`: bảo hành & sửa chữa
  - `G_3`: đơn hàng
  - `G_4`: xe máy bảo hành
  - `G_5`: hỗ trợ kỹ thuật từ xa
- Draft JSON schema cuối cuộc gọi:
  ```json
  {
    "category": "G_1",
    "fields": {},
    "post_call": {
      "short_summary": "",
      "sentimental_analysis": "",
      "emergency": "yes"
    }
  }
  ```

Cả hai chốt:
- Làm transcript mode trước để chắc chắn có bot chạy.
- Audio/ASR làm sau khi dialogue ổn.
- TTS để bonus, không ưu tiên đầu.

Deliverable cuối ngày:
- Repo structure có sẵn.
- `docs/architecture.md` bản draft.
- Category/field schema bản draft.
- Quyết định tech stack.

## Ngày 2: Xây Core Dialogue Và JSON Schema

Mục tiêu:
- Bot nhận transcript text và xử lý được ít nhất 2 category đầu.

Người 1 làm:
- Tạo CLI cơ bản:
  - `--interactive` để nhập từng turn.
  - `--transcript` để chạy một câu input.
- Tạo pipeline stub:
  - transcript input
  - dialogue manager
  - text response
  - final JSON

Người 2 làm:
- Viết `schemas.py` hoặc file schema tương đương:
  - category specs
  - required fields
  - field prompts
- Thiết kế flow hỏi field còn thiếu:
  - không hỏi lại field đã có
  - thiếu field nào hỏi field đó
  - khi đủ field thì finalize JSON
- Viết flow cho `G_1` và `G_2` trước.

Deliverable cuối ngày:
- CLI chạy được transcript mode.
- `G_1` và `G_2` chạy được happy path.
- Final JSON hợp lệ cho ít nhất 2 categories.

## Ngày 3: Hoàn Thành 5 Categories Và LLM/Dialog Engine

Mục tiêu:
- Đủ 5 categories end-to-end ở transcript mode.

Người 1 làm:
- Hoàn thiện dialogue manager hoặc tích hợp LLM backend.
- Nếu dùng LLM:
  - tạo prompt system rõ ràng
  - ép output JSON
  - có fallback nếu LLM output lỗi
- Nếu dùng state machine:
  - rule-based routing
  - extractor đơn giản cho phone, plate/VIN, name, location, condition

Người 2 làm:
- Hoàn thiện flow cho:
  - `G_3`: đơn hàng
  - `G_4`: bảo hành xe máy
  - `G_5`: hỗ trợ kỹ thuật từ xa
- Viết ít nhất 1 sample conversation/category.
- Review final JSON fields đúng brief.

Deliverable cuối ngày:
- Bot xử lý được cả 5 categories ở transcript mode.
- Có ít nhất 5 demo conversations.
- JSON có `category`, `fields`, `post_call`.

## Ngày 4: ASR Và Exception Handling

Mục tiêu:
- Có audio path khả dụng hoặc ít nhất ASR adapter rõ ràng.
- Bắt đầu xử lý các case khó.

Người 1 làm:
- Tích hợp ASR adapter:
  - audio file -> transcript
  - microphone -> wav -> transcript nếu kịp
- Log latency:
  - ASR time
  - dialogue time
  - total per turn
- Nếu ASR không ổn, ghi rõ fallback transcript mode.

Người 2 làm:
- Thiết kế và implement/document 8 exception cases:
  - Missing field
  - Customer corrects info
  - Ambiguous intent
  - Out-of-scope query
  - Unclear/garbled input
  - Emergency detected
  - Stuck after 2+ failed turns
  - Customer hangs up mid-call
- Với emergency:
  - ưu tiên an toàn
  - route về `G_1`
  - cung cấp hotline cứu hộ
  - không cố thu hết field thấp ưu tiên

Deliverable cuối ngày:
- Có ASR demo hoặc ASR fallback rõ ràng.
- Exception handling bản đầu chạy được.
- Partial JSON khi khách cúp máy.

## Ngày 5: Evaluation Framework

Mục tiêu:
- Có test scenarios và automated metrics.

Người 1 làm:
- Viết hoặc hỗ trợ script `evaluation/run_evaluation.py`.
- Script chạy nhiều scenarios và xuất `results.json`.
- Đo latency per turn.

Người 2 làm:
- Viết `evaluation/scenarios.json`:
  - ít nhất 10 normal scenarios
  - mỗi category ít nhất 2 scenarios
  - ít nhất 3 exception scenarios
  - nên có thêm emergency, correction, hang-up
- Định nghĩa metrics:
  - category accuracy
  - JSON validity
  - required-field completion
  - event/exception coverage
  - latency

Cả hai làm:
- Chạy evaluation.
- Ghi lại bot sai gì, vì sao sai.

Deliverable cuối ngày:
- Evaluation chạy tự động.
- Có `results.json`.
- Có số liệu metrics thật.

## Ngày 6: Report, README, Reproducibility

Mục tiêu:
- Người chấm đọc hiểu và chạy lại được.

Người 1 làm:
- Hoàn thiện `README.md`:
  - setup
  - install
  - chạy transcript demo
  - chạy audio demo nếu có
  - chạy evaluation
- Hoàn thiện `requirements.txt`.
- Thêm `.env.example`, không để credentials trong code.
- Test chạy lại từ môi trường sạch.

Người 2 làm:
- Hoàn thiện `docs/architecture.md`:
  - pipeline design
  - model choices
  - conversation flow
  - exception handling strategy
  - trade-offs
- Hoàn thiện `docs/evaluation_report.md`:
  - scenarios
  - metrics
  - results
  - failure analysis
  - latency breakdown
  - limitations

Deliverable cuối ngày:
- README chạy được.
- Architecture doc đầy đủ.
- Evaluation report đầy đủ.
- Không có secrets trong repo.

## Ngày 7: Final Test, Demo Script, Đóng Gói

Mục tiêu:
- Chuẩn bị bản nộp cuối và demo tự tin.

Cả hai làm:
- Chạy full checklist:
  ```powershell
  python -m pytest
  $env:PYTHONPATH="src"
  python evaluation\run_evaluation.py
  python -m vinfast_callbot.cli --interactive
  ```
- Chạy demo script 5-10 phút:
  - 1 case `G_1` emergency/cứu hộ
  - 1 case `G_2` hoặc `G_4` bảo hành
  - 1 case `G_3` đơn hàng
  - 1 case `G_5` kỹ thuật từ xa
  - 1 case correction hoặc hang-up
- Review output JSON.
- Review docs lần cuối.

Đóng gói submission:
- `src/`
- `evaluation/`
- `docs/`
- `tests/`
- `README.md`
- `requirements.txt`
- `.env.example`

Deliverable cuối ngày:
- Bản nộp cuối.
- Demo script.
- Evaluation results.
- Known limitations rõ ràng.

## Lịch Sync Hằng Ngày
Mỗi ngày sync 15 phút:
- Hôm qua làm gì?
- Hôm nay làm gì?
- Đang bị block ở đâu?
- Có thay đổi interface/schema nào ảnh hưởng người kia không?

## Quy Ước Làm Việc
- Người 1 không đổi JSON schema nếu chưa báo Người 2.
- Người 2 không đổi required fields nếu chưa báo Người 1.
- Mỗi ngày phải có một bản chạy được, dù còn đơn giản.
- Nếu ASR/LLM lỗi, luôn giữ transcript mode làm fallback demo.
- Không commit API key/token.

## Ưu Tiên Nếu Bị Trễ
Ưu tiên theo thứ tự:
1. Bot chạy được transcript mode.
2. Đủ 5 categories.
3. JSON đúng format.
4. Exception handling quan trọng: emergency, correction, missing field, hang-up.
5. Evaluation có metrics.
6. README và reports.
7. ASR audio demo.
8. TTS bonus.

Không nên làm TTS nếu core bot hoặc evaluation chưa ổn.

## Final Checklist
- Đủ 5 categories.
- Ít nhất 10 scenarios, mỗi category 2 scenarios.
- Ít nhất 3 exception scenarios, tốt nhất đủ 8 exception strategies trong docs.
- Final JSON đúng format.
- Missing fields là `null` khi partial/hang-up.
- Có automated metrics.
- Có latency per turn.
- Có failure analysis trung thực.
- README chạy lại được.
- `requirements.txt` đầy đủ.
- Không có credentials trong code.
