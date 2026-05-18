---
description: Tìm kiếm video YouTube và tóm tắt nội dung bằng yt-dlp + Whisper, xuất ra file .txt
argument-hint: <YouTube URL hoặc từ khóa tìm kiếm> [--model base|small|medium|large] [--output <thư mục>]
allowed-tools: Bash, Read, Write
---

Tóm tắt nội dung video YouTube từ đầu vào: **$ARGUMENTS**

---

## Quy trình

### Bước 1 — Kiểm tra dependencies

Chạy lệnh sau để kiểm tra yt-dlp và openai-whisper:

```powershell
python -c "import yt_dlp, whisper; print('Dependencies OK')"
```

Nếu lỗi `ModuleNotFoundError`, cài đặt bằng:
```powershell
pip install yt-dlp openai-whisper
```
Sau đó tiếp tục.

---

### Bước 2 — Phân tích đầu vào

Phân tích `$ARGUMENTS`:

- **Whisper model**: nếu có flag `--model <tên>` (base/small/medium/large), dùng model đó. Mặc định là `base`.
- **Output folder**: nếu có flag `--output <đường dẫn>`, dùng thư mục đó để lưu file. Mặc định là `E:\Claude-Code\AutoMedia\summaries`.
- **URL**: nếu phần còn lại chứa `youtube.com`, `youtu.be`, hoặc bắt đầu bằng `http` → đây là URL, chuyển thẳng sang Bước 4.
- **Từ khóa**: nếu không phải URL → đây là từ khóa tìm kiếm, thực hiện Bước 3.

---

### Bước 3 — Tìm kiếm video (chỉ khi đầu vào là từ khóa)

Chạy script tìm kiếm:

```powershell
python "E:\Claude-Code\AutoMedia\scripts\youtube_helper.py" search "<từ khóa>" 5
```

Script trả về JSON danh sách video. Hiển thị cho người dùng dạng bảng:

```
#  Tiêu đề                          Thời lượng  Kênh
1  <title>                          MM:SS       <uploader>
2  ...
```

Hỏi người dùng: **"Bạn muốn xem video số mấy? (nhập số 1-5)"**

Sau khi người dùng chọn, lấy URL tương ứng từ JSON rồi tiếp tục Bước 4.

---

### Bước 4 — Tải audio và transcribe

Chạy script transcribe (có thể mất vài phút tùy độ dài video):

```powershell
python "E:\Claude-Code\AutoMedia\scripts\youtube_helper.py" transcribe "<url>" <model>
```

Script trả về JSON gồm: `title`, `url`, `uploader`, `duration_seconds`, `description`, `transcript`, `language`.

Nếu có lỗi trong field `error`, thông báo lỗi cho người dùng và dừng.

---

### Bước 5 — Tóm tắt nội dung

Dùng transcript nhận được để tóm tắt nội dung video bằng **tiếng Việt**, theo format sau:

---

## 📺 [Tiêu đề video]

**Kênh:** [uploader] | **Thời lượng:** [duration phút giây] | **Ngôn ngữ gốc:** [language]
**Link:** [url]

---

### Nội dung chính
[Mô tả ngắn gọn 2-3 câu về chủ đề video]

### Các điểm quan trọng
- [Điểm 1]
- [Điểm 2]
- [Điểm 3]
- ...

### Kết luận
[Tóm tắt kết luận hoặc thông điệp chính của video trong 2-3 câu]

---

### Bước 6 — Xuất ra file .txt

Sau khi có nội dung tóm tắt hoàn chỉnh ở Bước 5:

1. **Tạo thư mục output** nếu chưa tồn tại:
   ```powershell
   New-Item -ItemType Directory -Force "<output_folder>"
   ```

2. **Đặt tên file** theo quy tắc:
   - Lấy tiêu đề video từ JSON metadata
   - Làm sạch tên file: xóa ký tự đặc biệt (`\ / : * ? " < > |`), thay khoảng trắng bằng `_`
   - Thêm timestamp: `YYYYMMDD_HHMMSS`
   - Ví dụ: `How_to_Learn_Python_20260518_143022.txt`

3. **Nội dung file** gồm 2 phần:

```
=== TÓM TẮT VIDEO YOUTUBE ===
Ngày tóm tắt: [datetime hiện tại]
URL: [url]
Kênh: [uploader]
Thời lượng: [duration]
Ngôn ngữ gốc: [language]
Whisper model: [model đã dùng]

=============================

[Toàn bộ nội dung tóm tắt từ Bước 5]

=============================
=== TRANSCRIPT GỐC ===

[Toàn bộ transcript từ Whisper]
```

4. **Dùng tool Write** để ghi file vào đường dẫn `<output_folder>/<tên_file>.txt`.

5. **Thông báo cho người dùng** đường dẫn file đã lưu:
   ```
   Đã lưu tóm tắt vào: <đường dẫn đầy đủ>
   ```

---

> **Lưu ý về model Whisper:**
> - `base` — nhanh, phù hợp video tiếng Anh rõ ràng
> - `small` — cân bằng tốc độ/chất lượng
> - `medium` / `large` — chính xác hơn, đặc biệt với tiếng Việt hoặc giọng khó nghe (chậm hơn)
