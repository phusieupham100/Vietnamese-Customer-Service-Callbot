# PHÂN CÔNG DỰ ÁN CALLBOT CHO NHÓM 2 NGƯỜI

## Người 1 — ASR, LLM Backend và Pipeline tích hợp

Người 1 chịu trách nhiệm xây dựng phần nền tảng để bot có thể chạy end-to-end.

### Công việc chính

* Thiết kế cấu trúc repository và môi trường chạy.
* Tích hợp ASR:

  * Nhận audio từ microphone.
  * Nhận audio từ file để dễ kiểm thử.
  * Chuyển giọng nói tiếng Việt thành transcript.
  * Xử lý trường hợp transcript rỗng hoặc không rõ.
* Tích hợp local LLM:

  * Ollama, llama.cpp, Hugging Face hoặc backend tương đương.
  * Quản lý request, timeout và lỗi kết nối.
* Xây dựng pipeline tổng:

```text
Microphone / Audio file
→ ASR
→ Transcript
→ Dialogue Engine
→ Text response
→ Final JSON
```

* Xây dựng session và lưu lịch sử hội thoại.
* Kết nối các module do Người 2 phát triển vào pipeline.
* Parse và validate JSON do LLM hoặc dialogue engine trả về.
* Ghi log:

  * ASR latency.
  * LLM latency.
  * Tổng latency mỗi lượt.
* Xây dựng transcript mode để test bot mà không cần ghi âm.
* Viết script chạy demo.
* Chuẩn bị:

  * `requirements.txt`
  * `.env.example`
  * Cấu hình model
  * Hướng dẫn cài đặt kỹ thuật
* Tích hợp TTS nếu phần bắt buộc đã hoàn thành.

### Đầu ra Người 1 cần bàn giao

* ASR module.
* Microphone input.
* Local LLM client.
* Session manager.
* Pipeline end-to-end.
* JSON validator.
* Latency logger.
* Script chạy bot và demo.

---

## Người 2 — Dialogue Logic, Exception Handling và Evaluation

Người 2 chịu trách nhiệm xây dựng bộ não điều khiển cuộc hội thoại và hệ thống đánh giá.

### Công việc chính

* Xây dựng schema cho 5 nhóm:

```text
G_1: Cứu hộ
G_2: Bảo hành và sửa chữa
G_3: Đơn hàng
G_4: Xe máy – Bảo hành
G_5: Hỗ trợ kỹ thuật từ xa
```

* Định nghĩa required fields và optional fields cho từng nhóm.
* Thiết kế logic phân loại category.
* Viết prompt cho LLM:

  * Intent classification.
  * Field extraction.
  * Response generation.
  * Post-call summary.
* Xây dựng dialogue manager:

  * Xác định field còn thiếu.
  * Chỉ hỏi field còn thiếu.
  * Không hỏi lại thông tin đã có.
  * Thu thập nhiều field trong một lượt nói.
  * Cho phép khách hàng sửa thông tin.
  * Cập nhật state sau mỗi lượt.
  * Xác định khi nào kết thúc cuộc gọi.
* Xây dựng logic xử lý 8 trường hợp ngoại lệ:

  * Thiếu thông tin.
  * Khách sửa thông tin.
  * Intent mơ hồ.
  * Câu hỏi ngoài phạm vi.
  * Input không rõ.
  * Emergency.
  * Bot không hiểu sau hai lượt.
  * Khách kết thúc giữa cuộc gọi.
* Thiết kế final JSON và post-call output.
* Xây dựng bộ test:

  * Tối thiểu hai case cho mỗi category.
  * Test cho toàn bộ exception cases.
  * Happy path và difficult cases.
* Viết automated evaluation:

  * Category accuracy.
  * Field extraction accuracy.
  * Field completion rate.
  * JSON validity rate.
  * Dialogue success rate.
  * Exception handling success rate.
  * No-reask rate.
* Tổng hợp kết quả và phân tích failure cases.
* Viết tài liệu:

  * Architecture.
  * Dialogue specification.
  * Exception handling.
  * Evaluation framework.
  * Evaluation report.
  * Limitations.

### Đầu ra Người 2 cần bàn giao

* Category schemas.
* Prompt templates.
* Dialogue manager.
* Field collection logic.
* Exception handler.
* Bộ test scenarios.
* Evaluation script và metrics.
* Architecture document.
* Evaluation report.

---

# Phần hai người phải cùng làm

## 1. Thống nhất interface ngay từ đầu

Hai người cần chốt một cấu trúc output chung, ví dụ:

```json
{
  "response_text": "Dạ anh/chị cho em xin số điện thoại liên hệ ạ.",
  "category": "G_1",
  "fields": {
    "full_name": "Nguyễn Văn Nam",
    "phone": null,
    "vehicle_model": "VF8"
  },
  "missing_fields": [
    "phone",
    "license_plate_vin"
  ],
  "status": "collecting",
  "transfer_to_human": false,
  "emergency": false
}
```

Người 2 phát triển dialogue engine theo cấu trúc này. Người 1 chỉ cần tích hợp vào pipeline.

## 2. Tích hợp thường xuyên

Không để đến cuối mới ghép code.

Sau khi mỗi module hoàn thành, cần tích hợp ngay:

```text
Transcript mode
→ Dialogue engine
→ Response
→ State update
→ Final JSON
```

Sau đó mới thay transcript mode bằng ASR microphone.

## 3. Kiểm thử chéo

* Người 1 kiểm tra dialogue engine có dễ tích hợp và ổn định không.
* Người 2 kiểm tra bot có hỏi đúng, không hỏi lại và không bịa thông tin không.
* Cả hai cùng chạy các test end-to-end.

## 4. Chuẩn bị demo

* Người 1 phụ trách vận hành hệ thống và giải thích pipeline.
* Người 2 phụ trách kịch bản hội thoại, evaluation và failure analysis.
* Cả hai cùng trình bày architecture và trade-off.

---

# Bảng phân công ngắn gọn

| Hạng mục               | Người 1                     | Người 2             |
| ---------------------- | --------------------------- | ------------------- |
| Repository, môi trường | Chính                       | Review              |
| ASR, microphone        | Chính                       | Test                |
| Local LLM backend      | Chính                       | Hỗ trợ prompt       |
| Pipeline tích hợp      | Chính                       | Hỗ trợ              |
| Session và history     | Chính                       | Định nghĩa state    |
| Category schemas       | Review                      | Chính               |
| Prompt engineering     | Tích hợp                    | Chính               |
| Dialogue manager       | Hỗ trợ tích hợp             | Chính               |
| Field collection       | Hỗ trợ tích hợp             | Chính               |
| Exception handling     | Tích hợp kỹ thuật           | Thiết kế và code    |
| JSON validation        | Chính                       | Định nghĩa schema   |
| Test scenarios         | Hỗ trợ                      | Chính               |
| Automated evaluation   | Viết test runner            | Viết metrics        |
| Latency measurement    | Chính                       | Tổng hợp kết quả    |
| Architecture document  | Review kỹ thuật             | Chính               |
| Evaluation report      | Cung cấp log                | Chính               |
| README                 | Phần cài đặt                | Phần sử dụng        |
| Demo cuối              | Vận hành                    | Kịch bản và báo cáo |
| TTS                    | Thực hiện nếu còn thời gian | Kiểm thử            |

---

# Nguyên tắc ưu tiên trong 7 ngày

Thứ tự ưu tiên nên là:

1. Transcript mode chạy ổn định.
2. Dialogue hoạt động đủ 5 category.
3. Thu thập đúng fields.
4. Sinh valid JSON.
5. Xử lý exception cases.
6. Microphone và ASR.
7. Evaluation và latency report.
8. README và tài liệu.
9. TTS nếu còn thời gian.

Không nên dành nhiều thời gian làm giao diện hoặc TTS khi dialogue, exception handling và evaluation chưa ổn định.
