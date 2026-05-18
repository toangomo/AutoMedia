---
name: makeup
description: >
  Dùng skill này khi người dùng muốn áp dụng makeup / trang điểm AI lên ảnh chân dung nữ.

  TRIGGER khi người dùng:
  - Kéo thả hoặc đính kèm ảnh chân dung và nhắc đến "makeup", "trang điểm", "làm đẹp",
    "chỉnh ảnh", "làm đẹp hơn", "son môi", "phấn má", "Korean style"
  - Nói "trang điểm cho ảnh này", "áp dụng makeup", "makeup ảnh này", "làm đẹp ảnh này"
  - Đưa đường dẫn file ảnh (.jpg, .jpeg, .png, .webp, .bmp) và muốn chỉnh makeup
  - Đưa đường dẫn folder và muốn makeup hàng loạt nhiều ảnh
  - Dùng từ khóa: "makeup", "trang điểm", "Korean makeup", "làm đẹp ảnh",
    "phong cách Hàn", "chỉnh son", "chỉnh má hồng", "skin smooth", "beauty"

  KHÔNG dùng khi:
  - Người dùng chỉ hỏi về makeup mà không có ảnh hoặc đường dẫn ảnh
  - Ảnh không phải chân dung người (phong cảnh, vật thể, động vật)
  - Người dùng muốn chỉnh sửa ảnh theo cách khác (resize, crop, xóa nền, filter màu)

version: 2.0.0
tools: [Bash, Write]
script: E:\Claude-Code\AutoMedia\scripts\makeup_helper.py
output_suffix: _makeup
---

## Skill: Makeup AI — Korean Style

### Bước 1 — Kiểm tra API key

```powershell
python "E:\Claude-Code\AutoMedia\scripts\makeup_helper.py" check
```

Kết quả JSON:
- `status: OK` → tiếp tục Bước 2
- `status: MISSING` → dừng, thông báo:

> API key chưa được cấu hình. Vui lòng chạy:
> ```
> ! python "E:\Claude-Code\AutoMedia\scripts\makeup_helper.py" setup "sk-..."
> ```
> Lấy key tại platform.openai.com/api-keys

---

### Bước 2 — Xác định loại input

Phân tích nội dung người dùng gửi:

| Loại | Dấu hiệu | Xử lý |
|------|----------|-------|
| Ảnh kéo thả | Message chứa `[Image: source: <path>]` | Trích `<path>` → Bước 3A |
| File ảnh | Đường dẫn có đuôi `.jpg/.jpeg/.png/.webp/.bmp` | → Bước 3A |
| Folder | Đường dẫn thư mục tồn tại | → Bước 3B |

**Trích path từ ảnh kéo thả:** Tìm pattern `[Image: source: <path>]` trong message, dùng `<path>` đó.

---

### Bước 3A — Xử lý ảnh đơn lẻ

```powershell
python "E:\Claude-Code\AutoMedia\scripts\makeup_helper.py" apply "<image_path>"
```

Nếu người dùng chỉ định thư mục output (`--output <dir>`):
```powershell
python "E:\Claude-Code\AutoMedia\scripts\makeup_helper.py" apply "<image_path>" "<output_dir>"
```

JSON trả về: `status`, `input`, `output`, `original_size`, `api_size`.
- `status: success` → Bước 4
- `error` → thông báo lỗi cụ thể, dừng

---

### Bước 3B — Xử lý cả folder

**3B.1 — Liệt kê ảnh:**
```powershell
python "E:\Claude-Code\AutoMedia\scripts\makeup_helper.py" list "<folder_path>"
```

Hiển thị danh sách ảnh tìm được, hỏi người dùng xác nhận trước khi chạy.

**3B.2 — Sau khi xác nhận:**
```powershell
python "E:\Claude-Code\AutoMedia\scripts\makeup_helper.py" folder "<folder_path>"
```

Nếu có thư mục output:
```powershell
python "E:\Claude-Code\AutoMedia\scripts\makeup_helper.py" folder "<folder_path>" "<output_dir>"
```

Script in tiến trình `[X/N] Đang xử lý: <tên file>` theo từng ảnh.

---

### Bước 4 — Báo cáo kết quả

**Ảnh đơn lẻ — thành công:**
```
Makeup hoàn tất!

  Input:         <đường dẫn ảnh gốc>
  Output:        <đường dẫn ảnh kết quả>
  Kích thước:    <WxH> (giữ nguyên kích thước gốc)
  API size:      <1024x1024 | 1536x1024 | 1024x1536>

Style Korean đã áp dụng:
  • Blush hồng nhạt — má và tip mũi
  • Son gradient hồng bóng
  • Da trắng mịn flawless
  • Giữ nguyên khuôn mặt, mắt, mũi, miệng
```

**Folder — hoàn tất:**
```
Đã xử lý <N> ảnh

  Thành công : <số>
  Thất bại   : <số>
  Output tại : <thư mục>

Chi tiết:
  <tên file> → <output path>  [<WxH>]
  <tên file> → LỖI: <lý do>
```

---

### Thông tin kỹ thuật

| Mục | Giá trị |
|-----|---------|
| Model | `gpt-image-2` (OpenAI Images Edit API) |
| Định dạng input | JPG, JPEG, PNG, WebP, BMP |
| Output | cùng định dạng gốc, hậu tố `_makeup` |
| Kích thước | resize về đúng kích thước ảnh gốc sau khi API xử lý |
| API size tự chọn | ngang → 1536×1024 · dọc → 1024×1536 · vuông → 1024×1024 |
| Bỏ qua | file đã có `_makeup` trong tên |
| Delay folder | 2 giây giữa mỗi ảnh |
| API key | Windows Credential Manager (mã hóa OS) — xem `makeup_prompt.txt` |
