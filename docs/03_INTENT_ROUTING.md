# 03 — Intent Routing

## 1. Mục tiêu

Phân loại cuộc gọi vào một trong năm category hoặc trả `category = null` khi chưa đủ thông tin.

Router phải dùng:

- transcript mới nhất;
- toàn bộ history;
- state hiện tại;
- loại phương tiện;
- nhu cầu dịch vụ;
- tín hiệu emergency;
- correction ở các lượt sau.

## 2. Nguyên tắc cốt lõi

```text
Triệu chứng xe
≠
Nhu cầu hỗ trợ
```

Ví dụ:

```text
Xe tôi không khởi động được.
```

chỉ cho biết tình trạng, chưa cho biết khách cần:

- cứu hộ;
- sửa chữa;
- bảo hành;
- hay hướng dẫn từ xa.

Không route sớm.

## 3. Internal signals

Signal Extractor nên trả:

```json
{
  "service_goal": "unknown",
  "vehicle_type": "unknown",
  "vehicle_model": null,
  "symptom": "không khởi động được",
  "can_move": null,
  "urgency": "normal",
  "explicit_rescue_request": false,
  "explicit_repair_request": false,
  "explicit_warranty_request": false,
  "explicit_order_request": false,
  "explicit_remote_support_request": false,
  "correction_detected": false
}
```

Giá trị `service_goal`:

```text
rescue
warranty_repair
order_support
motorbike_warranty
remote_support
unknown
```

## 4. Thứ tự định tuyến

```text
1. Emergency rõ ràng.
2. Nhu cầu đơn hàng rõ ràng.
3. Yêu cầu cứu hộ rõ ràng.
4. Yêu cầu hỗ trợ kỹ thuật từ xa rõ ràng.
5. Yêu cầu bảo hành hoặc sửa chữa rõ ràng.
6. Dùng loại phương tiện để phân biệt G_2 và G_4.
7. Nếu chỉ có triệu chứng, hỏi targeted clarification.
```

## 5. Quy tắc G_1 — Cứu hộ

Route `G_1` khi:

- khách nói rõ cần cứu hộ;
- khách yêu cầu kéo xe;
- khách yêu cầu điều người đến vị trí;
- khách xác nhận cần cứu hộ sau câu hỏi làm rõ;
- có emergency rõ ràng.

Không route `G_1` chỉ vì:

```text
xe hết pin
xe chết máy
xe không khởi động
xe báo lỗi
xe không đi được
```

Ví dụ:

```text
Khách: Xe tôi hết pin.
Bot: Dạ anh/chị có cần hỗ trợ cứu hộ ngay không ạ?
```

## 6. Quy tắc G_2 — Bảo hành và sửa chữa

Route `G_2` khi:

- nhu cầu là bảo hành hoặc sửa chữa;
- phương tiện là ô tô;
- khách muốn đặt lịch hoặc tìm trung tâm dịch vụ;
- khách hỏi lỗi có thuộc bảo hành không.

Ví dụ:

```text
Xe VF8 của tôi bị lỗi điều hòa, tôi muốn đặt lịch kiểm tra.
→ G_2
```

## 7. Quy tắc G_3 — Đơn hàng

Route `G_3` khi nội dung liên quan:

- trạng thái đơn;
- thời gian giao xe;
- đặt cọc;
- chuyển cọc;
- mã đơn;
- đại lý;
- cập nhật thông tin đơn;
- loại khách hàng.

Ví dụ:

```text
Tôi muốn kiểm tra bao giờ đơn xe của tôi được giao.
→ G_3
```

## 8. Quy tắc G_4 — Xe máy, bảo hành

Route `G_4` khi:

- phương tiện là xe máy điện;
- nhu cầu là bảo hành, sửa chữa hoặc tìm trung tâm dịch vụ.

Ví dụ:

```text
Xe Feliz của tôi bị lỗi pin, tôi muốn mang đi bảo hành.
→ G_4
```

Nếu nhu cầu sửa chữa đã rõ nhưng chưa rõ loại xe:

```text
Dạ anh/chị đang sử dụng ô tô hay xe máy điện ạ?
```

## 9. Quy tắc G_5 — Hỗ trợ kỹ thuật từ xa

Route `G_5` khi:

- khách yêu cầu hướng dẫn kiểm tra;
- khách hỏi cách thao tác;
- khách muốn xử lý lỗi từ xa;
- khách muốn thử bước khắc phục trước;
- khách hỏi về phần mềm, màn hình, ứng dụng hoặc kết nối và muốn được hướng dẫn.

Ví dụ:

```text
Màn hình xe bị treo, hướng dẫn tôi khởi động lại với.
→ G_5
```

Không route `G_5` chỉ vì xe có lỗi kỹ thuật.

## 10. Targeted clarification

Không hỏi:

```text
Anh/chị muốn cứu hộ, sửa chữa, đơn hàng, bảo hành xe máy
hay hỗ trợ kỹ thuật từ xa ạ?
```

Chỉ hỏi tín hiệu còn thiếu.

### Chưa rõ có cần cứu hộ

```text
Dạ anh/chị có cần hỗ trợ cứu hộ ngay không ạ?
```

### Đã rõ là sửa chữa nhưng chưa rõ loại xe

```text
Dạ anh/chị đang sử dụng ô tô hay xe máy điện ạ?
```

### Đã rõ có lỗi nhưng chưa rõ sửa hay hướng dẫn

```text
Dạ anh/chị muốn em hướng dẫn kiểm tra trước không ạ?
```

### Câu nói hoàn toàn chung chung

```text
Dạ anh/chị cần hỗ trợ vấn đề gì với xe ạ?
```

## 11. Candidate categories

Router có thể trả nhiều candidate nội bộ:

```json
{
  "category": null,
  "candidate_categories": ["G_1", "G_2", "G_5"],
  "missing_discriminator": "rescue_needed"
}
```

Candidate categories không được đọc trực tiếp cho khách.

## 12. Emergency routing

Emergency là trường hợp ưu tiên hơn flow thông thường.

Ví dụ emergency:

```text
Xe vừa tai nạn, có người bị thương.
Xe đang cháy.
Xe nằm ở vị trí nguy hiểm và có nguy cơ tai nạn tiếp.
```

Ví dụ không mặc định emergency:

```text
Xe không khởi động.
Xe hết pin.
Xe báo lỗi.
```

## 13. Sử dụng history

Router phải dùng toàn bộ history.

Ví dụ:

```text
Khách: Xe tôi không khởi động được.
Bot: Dạ anh/chị có cần hỗ trợ cứu hộ ngay không ạ?
Khách: Không, tôi đang ở nhà. Tôi muốn hỏi lỗi này có được bảo hành không.
```

Kết quả:

```text
G_2
```

Không tiếp tục giữ `G_1` chỉ vì câu đầu.

## 14. Thất bại định tuyến

- Lần 1 chưa rõ: hỏi targeted clarification.
- Lần 2 vẫn mơ hồ: hỏi lại ngắn hơn hoặc rephrase.
- Sau hai lượt thất bại: handoff.
- Không tự chọn category chỉ để tiếp tục.

## 15. Acceptance criteria

```text
"Xe tôi hết pin"
→ category = null
→ ASK_INTENT_CLARIFICATION

"Xe tôi hết pin, tôi cần cứu hộ"
→ G_1

"Xe VF8 bị lỗi, tôi muốn đặt lịch kiểm tra"
→ G_2

"Bao giờ đơn xe được giao?"
→ G_3

"Xe Feliz cần bảo hành"
→ G_4

"Hướng dẫn tôi khởi động lại màn hình"
→ G_5

"Xe không khởi động"
→ emergency = false

"Xe tai nạn, có người bị thương"
→ emergency = true
```

## 16. Metric bắt buộc cho router

```text
category_accuracy
premature_routing_rate
clarification_accuracy
routing_after_clarification_accuracy
emergency_false_positive_rate
```

## 17. Model xe như routing signal

Model xe giúp xác định loại phương tiện:

```text
model ô tô + nhu cầu bảo hành/sửa chữa → G_2
model xe máy + nhu cầu bảo hành/sửa chữa → G_4
```

Model xe không đủ để route `G_1` hoặc `G_5`.

```text
"VF 8 của tôi không khởi động"
→ category = null hoặc cần clarification

"VF 8 của tôi không khởi động, tôi cần cứu hộ"
→ G_1

"Feliz bị lỗi pin, tôi muốn bảo hành"
→ G_4

"VF 8 báo lỗi màn hình, hướng dẫn tôi kiểm tra"
→ G_5
```

Nếu model nhận dạng mơ hồ, router không được dựa vào candidate chưa xác nhận để chốt category.
