---
description: >
  Áp dụng makeup AI phong cách Korean lên ảnh chân dung nữ.
  Dùng skill này khi người dùng: gõ /makeup, kéo thả ảnh chân dung vào chat, nhắc đến "makeup",
  "trang điểm", "làm đẹp ảnh", "Korean makeup", hoặc muốn chỉnh sửa ảnh portrait.
  Hỗ trợ ảnh đơn lẻ (kéo thả hoặc đường dẫn) và xử lý hàng loạt cả folder.
version: 2.0.0
argument-hint: <[Image] | đường dẫn ảnh | đường dẫn folder> [--output <thư mục>]
allowed-tools: Bash, Read, Write
---

# Makeup AI — Korean Style

Đầu vào nhận được: **$ARGUMENTS**

---

## Bước 1 — Kiểm tra API key

```powershell
python "E:\Claude-Code\AutoMedia\scripts\makeup_helper.py" check
```

Kết quả JSON:
- `status: OK` → tiếp tục Bước 2
- `status: MISSING` → dừng và hiển thị:

> API key chưa được cấu hình. Chạy lệnh sau để lưu key vào Windows Credential Manager:
> ```
> ! python "E:\Claude-Code\AutoMedia\scripts\makeup_helper.py" setup "sk-..."
> ```
> Lấy key tại platform.openai.com/api-keys

---

## Bước 2 — Phân tích đầu vào

Tách `$ARGUMENTS`:
- **`--output <thư mục>`** nếu có → dùng làm thư mục lưu kết quả
- **Phần còn lại** xác định loại input:

| Loại | Nhận biết | Xử lý |
|------|-----------|-------|
| Ảnh kéo thả | chứa `[Image` hoặc không có đường dẫn rõ ràng | Bước 3A — đọc path từ metadata `[Image: source: <path>]` trong message |
| File ảnh | đuôi `.jpg/.jpeg/.png/.webp/.bmp` | Bước 3A |
| Folder | là đường dẫn thư mục tồn tại | Bước 3B |

**Lấy path từ ảnh kéo thả:** Tìm dòng `[Image: source: <path>]` trong nội dung message hiện tại, dùng `<path>` đó làm image_path.

---

## Bước 3A — Xử lý ảnh đơn lẻ

```powershell
python "E:\Claude-Code\AutoMedia\scripts\makeup_helper.py" apply "<image_path>"
```

Nếu có `--output <dir>`:
```powershell
python "E:\Claude-Code\AutoMedia\scripts\makeup_helper.py" apply "<image_path>" "<output_dir>"
```

Kết quả JSON trả về `status`, `input`, `output`, `original_size`, `api_size`.
- `status: success` → tiếp tục Bước 4
- `error` → hiển thị lỗi cụ thể và dừng

---

## Bước 3B — Xử lý cả folder

**3B.1 — Liệt kê và xác nhận:**
```powershell
python "E:\Claude-Code\AutoMedia\scripts\makeup_helper.py" list "<folder_path>"
```

Hiển thị danh sách ảnh tìm thấy, hỏi người dùng xác nhận trước khi chạy hàng loạt.

**3B.2 — Sau khi xác nhận:**
```powershell
python "E:\Claude-Code\AutoMedia\scripts\makeup_helper.py" folder "<folder_path>"
```

Với `--output`:
```powershell
python "E:\Claude-Code\AutoMedia\scripts\makeup_helper.py" folder "<folder_path>" "<output_dir>"
```

Script in tiến trình `[X/N] Đang xử lý: <tên file>` ra stderr theo từng ảnh.

---

## Bước 4 — Báo cáo kết quả

### Ảnh đơn lẻ — thành công:
```
Makeup hoàn tất!

  Input:         <đường dẫn ảnh gốc>
  Output:        <đường dẫn ảnh kết quả>
  Kích thước:    <WxH gốc> (giữ nguyên)
  API size dùng: <1024x1024 | 1536x1024 | 1024x1536>

Style Korean đã áp dụng:
  • Blush hồng nhạt — má và tip mũi
  • Son gradient hồng bóng
  • Da trắng mịn flawless
  • Giữ nguyên cấu trúc khuôn mặt
```

### Folder — hoàn tất:
```
Đã xử lý <N> ảnh

  Thành công: <số>
  Thất bại:   <số>
  Output tại: <thư mục>

Chi tiết:
  <tên file> → <output path>  (WxH)
  <tên file> → LỖI: <lý do>
```

---

## Thông tin kỹ thuật

| Mục | Giá trị |
|-----|---------|
| Model | `gpt-image-2` (OpenAI) |
| Định dạng input | JPG, JPEG, PNG, WebP, BMP |
| Output | cùng định dạng gốc, hậu tố `_makeup` |
| Kích thước output | resize về đúng kích thước ảnh gốc sau khi API xử lý |
| API size tự chọn | ngang → 1536×1024 · dọc → 1024×1536 · vuông → 1024×1024 |
| Bỏ qua tự động | file có `_makeup` trong tên |
| Delay folder | 2 giây giữa mỗi ảnh (tránh rate limit) |
| API key storage | Windows Credential Manager (mã hóa OS) |
