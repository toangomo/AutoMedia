---
name: avif-convert
description: >
  Dùng skill này khi người dùng muốn chuyển đổi ảnh sang định dạng AVIF để nén file nhỏ hơn.

  TRIGGER khi người dùng:
  - Đưa đường dẫn file ảnh (.jpg, .jpeg, .png, .webp, .bmp, .tiff, .gif) và nói "convert avif",
    "chuyển avif", "sang avif", "nén avif", "đổi sang avif"
  - Đưa đường dẫn folder và muốn convert hàng loạt sang avif
  - Dùng từ khóa: "avif", "convert ảnh", "nén ảnh avif", "chuyển định dạng avif",
    "compress avif", "image to avif", "ảnh sang avif", "đổi định dạng ảnh"
  - Nói "convert tất cả ảnh trong folder này sang avif"
  - Kéo thả file ảnh và nhắc đến "avif"

  KHÔNG dùng khi:
  - Người dùng muốn convert sang định dạng khác (jpg, png, webp — không phải avif)
  - Người dùng chỉ hỏi về AVIF mà không có file/folder
  - Người dùng muốn chỉnh sửa nội dung ảnh (resize, crop, filter, makeup)

version: 1.0.0
tools: [Bash, Write]
script: E:\Claude-Code\AutoMedia\scripts\avif_convert_helper.py
output_subfolder: avif
default_quality: 80
---

## Skill: AVIF Convert

### Bước 1 — Kiểm tra dependencies

```powershell
python "E:\Claude-Code\AutoMedia\scripts\avif_convert_helper.py" check
```

Kết quả JSON:
- `status: OK` → tiếp tục Bước 2
- `status: MISSING` → chạy setup rồi check lại:

```powershell
python "E:\Claude-Code\AutoMedia\scripts\avif_convert_helper.py" setup
```

Nếu setup thất bại, dừng và thông báo:
> Không thể cài đặt thư viện AVIF. Vui lòng chạy thủ công:
> ```
> ! pip install pillow pillow-avif-plugin
> ```

---

### Bước 2 — Xác định loại input

Phân tích nội dung người dùng gửi:

| Loại | Dấu hiệu | Xử lý |
|------|----------|-------|
| File ảnh đơn | Đường dẫn có đuôi `.jpg/.jpeg/.png/.webp/.bmp/.tiff/.gif` | → Bước 3A |
| Ảnh kéo thả | Message chứa `[Image: source: <path>]` | Trích `<path>` → Bước 3A |
| Folder | Đường dẫn thư mục tồn tại | → Bước 3B |

**Quality tùy chỉnh:** Nếu người dùng chỉ định chất lượng (vd "quality 90", "chất lượng cao"), lấy số đó (0–100). Mặc định: `80`.

---

### Bước 3A — Convert ảnh đơn lẻ

Output mặc định: lưu cùng folder với file gốc.
Nếu người dùng chỉ định folder output, dùng folder đó.

```powershell
python "E:\Claude-Code\AutoMedia\scripts\avif_convert_helper.py" convert "<image_path>"
```

Với folder output tùy chỉnh:
```powershell
python "E:\Claude-Code\AutoMedia\scripts\avif_convert_helper.py" convert "<image_path>" "<output_dir>"
```

Với quality tùy chỉnh:
```powershell
python "E:\Claude-Code\AutoMedia\scripts\avif_convert_helper.py" convert "<image_path>" "<output_dir>" <quality>
```

JSON trả về: `status`, `input`, `output`, `dimensions`, `src_bytes`, `dest_bytes`, `compression`.
- `status: success` → Bước 4
- `status: error` → thông báo lỗi cụ thể, dừng

---

### Bước 3B — Convert cả folder

**3B.1 — Liệt kê ảnh trước:**
```powershell
python "E:\Claude-Code\AutoMedia\scripts\avif_convert_helper.py" list "<folder_path>"
```

Hiển thị danh sách file và tổng dung lượng, **hỏi người dùng xác nhận** trước khi convert.

**3B.2 — Sau khi xác nhận, convert toàn bộ:**

Output mặc định: subfolder `avif/` bên trong folder gốc.

```powershell
python "E:\Claude-Code\AutoMedia\scripts\avif_convert_helper.py" folder "<folder_path>"
```

Với folder output tùy chỉnh:
```powershell
python "E:\Claude-Code\AutoMedia\scripts\avif_convert_helper.py" folder "<folder_path>" "<output_dir>"
```

Với quality tùy chỉnh:
```powershell
python "E:\Claude-Code\AutoMedia\scripts\avif_convert_helper.py" folder "<folder_path>" "<output_dir>" <quality>
```

Script in tiến trình `[X/N] Converting: <tên file>` cho mỗi ảnh.

---

### Bước 4 — Báo cáo kết quả

**Ảnh đơn lẻ — thành công:**
```
Convert AVIF hoàn tất!

  Input:        <đường dẫn gốc>
  Output:       <đường dẫn .avif>
  Kích thước:   <WxH>
  Dung lượng:   <src KB> → <dest KB> (giảm X%)
```

**Folder — hoàn tất:**
```
Đã convert <N> ảnh sang AVIF

  Thành công   : <số>
  Thất bại     : <số>
  Output tại   : <thư mục>
  Nén tổng thể : giảm X%

Chi tiết:
  <tên file> → <output path>  [<WxH>]  giảm X%
  <tên file> → LỖI: <lý do>
```

---

### Thông tin kỹ thuật

| Mục | Giá trị |
|-----|---------|
| Thư viện | Pillow + `pillow-avif-plugin` |
| Định dạng input | JPG, JPEG, PNG, WebP, BMP, TIFF, GIF |
| Định dạng output | `.avif` |
| Quality mặc định | 80 (0–100, cao hơn = chất lượng cao hơn) |
| Output đơn lẻ | Cùng folder với file gốc |
| Output folder | Subfolder `avif/` bên trong folder gốc |
| Transparency | Hỗ trợ (RGBA) — PNG, WebP có alpha |
| Bỏ qua | File `.avif` đã có trong folder khi list |
