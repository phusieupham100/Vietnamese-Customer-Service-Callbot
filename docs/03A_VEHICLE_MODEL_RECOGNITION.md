# 03A — Vehicle Model Recognition

## 1. Mục tiêu

Chuẩn hóa tên model xe từ transcript ASR về một tên canonical, xác định loại phương tiện và yêu cầu xác nhận khi kết quả chưa chắc chắn.

Module này hỗ trợ:

- `G_1.vehicle_model`
- `G_1.vehicle_type`
- `G_2.vehicle_model`
- `G_4.vehicle_line`
- `G_5.vehicle_line`
- Intent routing giữa `G_2` và `G_4`

Model xe chỉ là tín hiệu nhận dạng phương tiện. Model xe không tự quyết định khách cần cứu hộ, sửa chữa hay hỗ trợ từ xa.

## 2. Kiến trúc

```text
Transcript cuối từ ASR
        ↓
Vehicle Mention Extractor
        ↓
Text Normalizer
        ↓
Canonical / Alias Matcher
        ├── exact match
        ├── alias match
        ├── fuzzy unique candidate
        ├── ambiguous candidates
        └── unknown
        ↓
Confirmation Policy
        ↓
VehicleMatchResult
        ↓
Field Mapping + Intent Router
```

## 3. Danh sách canonical model

### 3.1 Ô tô

```text
EC VAN
FADIL
Ebus
Green Bus 10M
Green Bus 6M
Green Bus 8M
LacHong / Lạc Hồng
LUX A2.0
LUX SA2.0
LUX V8 / President
Minio Green
Herio Green
Nerio Green
Limo Green
VF 3
VF 5
VF 6
VF 7
VF 8
VF 9
VF MPV 7
VF e34
VF Wild
```

### 3.2 Xe máy điện

```text
Drgn Fly
Evo Grand
Evo Grand Lite
Evo lite Neo
Evo Neo
EVO200
EVO200 LITE
Feliz
Feliz 2025
FELIZ II
Feliz Lite
Feliz Neo
FELIZ S
FLAZZ
Impes
Klara A1
Klara A2
Klara Neo
Klara S
KLARA S - 2022
KLARA S2
Ludo
Motio
TEMPEST
Theon
THEON - 1
THEON S
Vento
Vento Neo
VENTO S
VeroX
VeroX Max
VIPER
ZGOO
```

## 4. Source of truth

Danh sách model nên được lưu ở:

```text
resources/vehicle_models.yaml
```

Tài liệu này mô tả quy tắc. File YAML là nguồn dữ liệu mà code đọc khi chạy.

Mỗi model nên có:

```yaml
canonical_name: "VF 8"
vehicle_type: "car"
aliases:
  - "vf8"
  - "vf 8"
  - "v f 8"
  - "vê ép tám"
  - "ép tám"
```

## 5. Vehicle type

Giá trị nội bộ:

```text
car
motorbike
unknown
```

Mapping:

- Model trong danh sách ô tô → `car`
- Model trong danh sách xe máy điện → `motorbike`
- Không match được → `unknown`

Đối với final JSON của `G_1`, `vehicle_type` phải được map theo format mà hệ thống thống nhất, ví dụ `car` hoặc `motorbike`.

## 6. Chuẩn hóa text

Normalizer phải hỗ trợ:

- lowercase để so khớp;
- trim khoảng trắng;
- gộp nhiều khoảng trắng;
- chuẩn hóa dấu gạch ngang;
- chuẩn hóa dấu chấm trong tên model;
- giữ lại chữ số có ý nghĩa;
- hỗ trợ text có dấu và không dấu;
- hỗ trợ viết liền hoặc viết cách;
- hỗ trợ cách đọc chữ cái tiếng Việt từ ASR.

Ví dụ:

```text
VF8
vf 8
V F 8
vê ép tám
ép tám
```

có thể được map về:

```text
VF 8
```

Normalizer chỉ chuẩn hóa để so khớp. Final value phải dùng canonical name.

## 7. Thứ tự matching

### 7.1 Exact canonical match

Nếu text sau normalization trùng canonical name:

```text
status = confirmed
match_type = exact
```

### 7.2 Exact alias match

Nếu text trùng alias đã định nghĩa:

```text
status = confirmed
match_type = alias
```

### 7.3 Fuzzy unique candidate

Fuzzy matching chỉ dùng để tạo candidate, không tự ghi final field.

```text
status = needs_confirmation
match_type = fuzzy
```

### 7.4 Ambiguous candidate

Nếu có nhiều model gần nhau:

```text
canonical_name = null
status = needs_confirmation
match_type = ambiguous
```

### 7.5 Unknown

Nếu không match:

```text
canonical_name = null
vehicle_type = unknown
status = unknown
match_type = unknown
```

Không map model lạ sang model gần nhất.

## 8. VehicleMatchResult

```json
{
  "raw_text": "ép tám",
  "canonical_name": "VF 8",
  "vehicle_type": "car",
  "match_type": "alias",
  "confidence": 0.98,
  "status": "confirmed",
  "candidates": []
}
```

Trường hợp mơ hồ:

```json
{
  "raw_text": "green bus tám",
  "canonical_name": null,
  "vehicle_type": "car",
  "match_type": "ambiguous",
  "confidence": 0.66,
  "status": "needs_confirmation",
  "candidates": [
    "Green Bus 6M",
    "Green Bus 8M",
    "Green Bus 10M"
  ]
}
```

Trường hợp ngoài catalog nhưng khách xác nhận:

```json
{
  "raw_text": "Zumo",
  "canonical_name": "Zumo",
  "vehicle_type": "unknown",
  "match_type": "unknown",
  "confidence": 1.0,
  "status": "unknown_confirmed",
  "candidates": []
}
```

## 9. Confirmation policy

### 9.1 Exact hoặc alias chắc chắn

Có thể lưu ngay nếu:

- final transcript;
- confidence đủ cao;
- không xung đột với state trước đó.

### 9.2 Fuzzy hoặc ambiguous

Phải hỏi xác nhận.

Ví dụ:

```text
Dạ anh/chị đang sử dụng Green Bus 8M đúng không ạ?
```

Nếu có đúng hai candidate phù hợp:

```text
Dạ anh/chị đang dùng Feliz Lite hay Feliz Neo ạ?
```

Không đọc danh sách dài.

### 9.3 Unknown model

Hỏi xác nhận một lần:

```text
Dạ em xin xác nhận tên dòng xe là Zumo đúng không ạ?
```

Nếu khách xác nhận:

- lưu raw value;
- đánh dấu `unknown_confirmed`;
- không map sang `ZGOO`.

## 10. Các nhóm dễ nhầm

### 10.1 Green Bus

```text
Green Bus 6M
Green Bus 8M
Green Bus 10M
```

Không bỏ mất hậu tố số.

### 10.2 Feliz

```text
Feliz
Feliz 2025
FELIZ II
Feliz Lite
Feliz Neo
FELIZ S
```

Nếu khách nói rõ `Feliz`, nhận đúng model `Feliz`. Không tự đổi sang variant khác.

### 10.3 Evo

```text
Evo Grand
Evo Grand Lite
Evo lite Neo
Evo Neo
EVO200
EVO200 LITE
```

Giữ nguyên hậu tố `Grand`, `Lite`, `Neo`, `200`.

### 10.4 Klara

```text
Klara A1
Klara A2
Klara Neo
Klara S
KLARA S - 2022
KLARA S2
```

Không map `Klara S` sang `KLARA S2`.

### 10.5 Theon

```text
Theon
THEON - 1
THEON S
```

Giữ ba canonical name riêng.

### 10.6 VF 8 và LUX V8

Nếu transcript chỉ có `V8` hoặc confidence thấp:

```text
Dạ anh/chị đang nói VF 8 hay LUX V8 ạ?
```

## 11. Alias khởi điểm

Các alias dưới đây là tập ban đầu. Alias thực tế phải tiếp tục được bổ sung từ log ASR.

```yaml
"VF 8":
  - "vf8"
  - "vf 8"
  - "v f 8"
  - "vê ép tám"
  - "ép tám"

"VF e34":
  - "vfe34"
  - "vf e34"
  - "vf e 34"
  - "vê ép e ba tư"

"LacHong / Lạc Hồng":
  - "lac hong"
  - "lạc hồng"
  - "lachong"

"EVO200":
  - "evo200"
  - "evo 200"
  - "evo hai trăm"

"EVO200 LITE":
  - "evo200 lite"
  - "evo 200 lite"
  - "evo hai trăm lite"

"FELIZ II":
  - "feliz ii"
  - "feliz 2"
  - "feliz hai"

"KLARA S2":
  - "klara s2"
  - "klara s 2"
  - "klara ét hai"

"Green Bus 8M":
  - "green bus 8m"
  - "green bus tám mét"
```

## 12. Mapping vào category fields

```text
G_1.vehicle_model ← canonical_name hoặc raw unknown_confirmed
G_1.vehicle_type  ← vehicle_type

G_2.vehicle_model ← canonical car model

G_4.vehicle_line  ← canonical motorbike model

G_5.vehicle_line  ← canonical model phù hợp
```

Quy tắc:

- `G_2` không nhận model xe máy.
- `G_4` không nhận model ô tô.
- Nếu model xung đột với category, policy phải hỏi làm rõ hoặc xem xét đổi category.
- Không đưa `raw_text`, confidence, candidates vào final JSON.

## 13. Tác động đến intent routing

Model là routing signal:

```text
model ô tô + nhu cầu bảo hành/sửa chữa → G_2
model xe máy + nhu cầu bảo hành/sửa chữa → G_4
```

Model không đủ để route:

```text
"VF 8 của tôi không khởi động"
→ category vẫn có thể là null
```

Ví dụ đúng:

```text
"VF 8 không khởi động, tôi cần cứu hộ"
→ G_1

"Feliz bị lỗi pin, tôi muốn bảo hành"
→ G_4

"VF 8 báo lỗi màn hình, hướng dẫn tôi kiểm tra"
→ G_5
```

## 14. ASR hotwords

Nên sinh:

```text
resources/asr_hotwords.txt
```

Từ canonical names và alias quan trọng.

Hotwords chỉ hỗ trợ nhận dạng âm thanh. Dialogue layer vẫn phải normalize, match và validate.

## 15. Module triển khai dự kiến

```text
src/vinfast_callbot/
  vehicle_catalog.py
  vehicle_normalizer.py
  vehicle_matcher.py

resources/
  vehicle_models.yaml
  asr_hotwords.txt

tests/
  test_vehicle_matcher.py
```

## 16. Metrics

```text
vehicle_model_exact_match
vehicle_type_accuracy
vehicle_alias_resolution_rate
vehicle_model_confirmation_accuracy
unknown_model_false_mapping_rate
```

## 17. Test bắt buộc

```text
"ép tám"
→ VF 8

"VF8"
→ VF 8

"Feliz"
→ Feliz

"Feliz hai"
→ FELIZ II

"Green Bus tám mét"
→ Green Bus 8M

"Klara S"
→ Klara S

"Zumo"
→ không map thành ZGOO

"VF 8 của tôi không khởi động"
→ không tự route G_1

"Feliz bị lỗi pin, tôi muốn bảo hành"
→ G_4
```

## 18. Acceptance criteria

- Load được toàn bộ catalog.
- Mọi canonical model exact-match đúng.
- Alias phổ biến match đúng.
- Suy ra đúng vehicle type.
- Fuzzy match không tự commit field.
- Không false-map model ngoài catalog.
- Không tự đổi variant gần nhau.
- Model confirmed không bị hỏi lại.
- Correction model cập nhật đúng.
- Final JSON chỉ chứa canonical name hoặc raw unknown-confirmed value.
