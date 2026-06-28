# 02 — Category Schemas

## 1. Mục đích

Tài liệu này là source of truth duy nhất cho field của năm category.

Không đổi tên field để phù hợp với code cũ.

## 2. G_1 — Cứu hộ

### Goal

Nhận báo cáo sự cố và chuẩn bị thông tin để điều phối hỗ trợ tại chỗ hoặc kéo xe.

### Fields

| Field | Bắt buộc | Mô tả |
|---|---:|---|
| `full_name` | Có | Họ tên khách hàng |
| `phone` | Có | Số điện thoại liên hệ |
| `vehicle_model` | Có | Dòng xe hoặc model |
| `license_plate_vin` | Có | Biển số hoặc VIN |
| `vehicle_type` | Có | Loại phương tiện |
| `current_odo` | Có | Số kilomet hiện tại |
| `current_location` | Có | Vị trí hiện tại |
| `city_name` | Có | Tỉnh hoặc thành phố |
| `vehicle_condition` | Có | Tình trạng xe |

### Field priority đề xuất

```text
emergency/safety
current_location
city_name
phone
full_name
vehicle_model
vehicle_type
license_plate_vin
vehicle_condition
current_odo
```

### Completion rule

Hoàn tất khi category đã xác nhận và tất cả field bắt buộc đã có, trừ khi:

- emergency cần handoff sớm;
- khách kết thúc giữa chừng;
- hệ thống chuyển người thật.

## 3. G_2 — Bảo hành và sửa chữa

### Goal

Tư vấn bảo hành hoặc sửa chữa và cung cấp thông tin trung tâm dịch vụ.

### Fields

| Field | Bắt buộc | Mô tả |
|---|---:|---|
| `full_name` | Có | Họ tên khách hàng |
| `owner_phone` | Có | Số điện thoại chủ xe |
| `vehicle_model` | Có | Dòng xe |
| `vehicle_usage_type` | Có | Mục đích sử dụng xe |
| `license_plate_vin` | Có | Biển số hoặc VIN |
| `service_center` | Có | Trung tâm dịch vụ |
| `vehicle_condition` | Có | Tình trạng xe |

### Field priority đề xuất

```text
vehicle_condition
vehicle_model
vehicle_usage_type
service_center
owner_phone
full_name
license_plate_vin
```

## 4. G_3 — Đơn hàng

### Goal

Hỗ trợ trạng thái đơn hàng, giao xe, chuyển cọc hoặc cập nhật thông tin đơn.

### Fields

| Field | Bắt buộc | Mô tả |
|---|---:|---|
| `full_name` | Có | Họ tên khách hàng |
| `order_phone` | Có | Số điện thoại dùng cho đơn hàng |
| `order_code_dealer` | Có | Mã đơn hàng hoặc đại lý |
| `customer_type` | Có | Loại khách hàng |

### Lưu ý

Nhóm này không yêu cầu:

- biển số;
- VIN;
- ODO;
- tình trạng xe.

## 5. G_4 — Xe máy, bảo hành

### Goal

Tư vấn bảo hành hoặc sửa chữa xe máy điện và hướng dẫn đến trung tâm dịch vụ phù hợp.

### Fields

| Field | Bắt buộc | Mô tả |
|---|---:|---|
| `full_name` | Có | Họ tên khách hàng |
| `phone` | Có | Số điện thoại liên hệ |
| `vehicle_line` | Có | Dòng xe máy điện |
| `license_plate_vin` | Có | Biển số hoặc VIN |
| `current_location` | Có | Vị trí hiện tại |
| `vehicle_condition` | Có | Tình trạng xe |

## 6. G_5 — Hỗ trợ kỹ thuật từ xa

### Goal

Hướng dẫn khách kiểm tra hoặc xử lý lỗi từ xa; chuyển sang trung tâm dịch vụ nếu không giải quyết được.

### Fields

| Field | Bắt buộc | Mô tả |
|---|---:|---|
| `full_name` | Có | Họ tên khách hàng |
| `phone` | Có | Số điện thoại liên hệ |
| `license_plate_vin` | Có | Biển số hoặc VIN |
| `vehicle_line` | Có | Dòng xe |
| `current_odo` | Không | ODO hiện tại |
| `vehicle_condition_details` | Có | Chi tiết tình trạng, gồm phiên bản phần mềm nếu liên quan |

## 7. Field normalization

Có thể dùng tên nội bộ chung, nhưng final output phải map về đúng field của category.

Ví dụ nội bộ:

```text
contact_phone
vehicle_identifier
```

Khi xuất:

```text
G_1.contact_phone → phone
G_2.contact_phone → owner_phone
G_3.contact_phone → order_phone
G_4.contact_phone → phone
G_5.contact_phone → phone
```

Không để tên nội bộ xuất hiện trong final JSON.

## 8. Critical fields

Các field sau cần xác nhận khi ASR không chắc chắn:

```text
phone
owner_phone
order_phone
license_plate_vin
order_code_dealer
current_odo
```

## 9. Dữ liệu thiếu

- Trong state nội bộ có thể chưa tạo key cho field chưa biết.
- Trong final JSON phải có đầy đủ key của category.
- Giá trị chưa thu thập được phải là `null`.

## 10. Không tự thêm field vào final schema

Có thể có internal signals như:

```text
safety_status
can_move
rescue_requested
remote_support_requested
```

nhưng không thêm chúng vào `fields` của final JSON nếu brief không yêu cầu.

## 11. Mapping model xe

```text
G_1.vehicle_model ← canonical model name hoặc raw unknown-confirmed value
G_1.vehicle_type  ← vehicle type từ catalog

G_2.vehicle_model ← canonical car model

G_4.vehicle_line  ← canonical motorbike model

G_5.vehicle_line  ← canonical model phù hợp
```

Quy tắc:

- `G_2` chỉ nhận model ô tô.
- `G_4` chỉ nhận model xe máy điện.
- `G_1` có thể nhận ô tô hoặc xe máy điện.
- `G_5` có thể nhận model phù hợp với cuộc gọi.
- Không thêm `raw_model`, `match_confidence`, `match_type` hoặc candidates vào final JSON.
- Model recognition phải tuân theo `03A_VEHICLE_MODEL_RECOGNITION.md`.
