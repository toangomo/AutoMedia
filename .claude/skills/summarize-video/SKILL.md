---
name: summarize-video
description: >
  Dùng skill này khi người dùng muốn tóm tắt, xem nội dung, hoặc hiểu một video.

  TRIGGER khi người dùng:
  - Dán một YouTube URL và hỏi về nội dung, muốn tóm tắt, hoặc muốn biết video nói gì
  - Đưa đường dẫn file video/audio local (.mp4, .avi, .mkv, .mov, .mp3, .m4a, v.v.)
  - Đưa đường dẫn folder và yêu cầu xử lý các video trong đó
  - Dùng các từ khóa: "tóm tắt video", "video này nói gì", "nội dung clip",
    "xem video", "transcribe", "summarize video", "video nói về gì",
    "tóm tắt bài giảng", "tóm tắt cuộc họp"
  - Tìm kiếm video YouTube để tóm tắt ("tìm video về X rồi tóm tắt")

  KHÔNG dùng khi:
  - Người dùng chỉ hỏi thông tin về video mà không có URL/file
  - Người dùng muốn tải video về (không cần tóm tắt)

tools: [Bash, Write]
script: E:\Claude-Code\AutoMedia\scripts\video_helper.py
output_dir: summaries
---

## Skill: Tóm tắt Video

### Bước 1 — Xác định loại input

Phân tích input từ người dùng:

| Loại | Dấu hiệu | Xử lý |
|------|----------|-------|
| YouTube URL | `youtube.com`, `youtu.be`, `shorts/` | → Bước 2A |
| File local | đường dẫn có extension media | → Bước 2B |
| Folder | đường dẫn thư mục tồn tại | → Bước 2C |
| Từ khóa | không có URL/path | → Bước 2D |

Tham số `--model` nếu người dùng chỉ định (base/small/medium/large). Mặc định: `base`.

---

### Bước 2A — YouTube URL

```powershell
python "E:\Claude-Code\AutoMedia\scripts\video_helper.py" transcribe-youtube "<url>" <model>
```

Script thử theo thứ tự:
1. **YouTube Caption API** — lấy phụ đề trực tiếp, nhanh, không bị chặn
2. **Whisper fallback** — tải audio rồi transcribe nếu không có phụ đề

→ Bước 3

---

### Bước 2B — File video/audio local

```powershell
python "E:\Claude-Code\AutoMedia\scripts\video_helper.py" transcribe-local "<file_path>" <model>
```

→ Bước 3

---

### Bước 2C — Folder local

```powershell
python "E:\Claude-Code\AutoMedia\scripts\video_helper.py" list-videos "<folder_path>"
```

Hiển thị danh sách file tìm được, hỏi người dùng xác nhận trước khi xử lý.
Xử lý từng file: lặp lại **Bước 2B → Bước 3 → Bước 4** cho mỗi file.
Sau cùng, in báo cáo tổng kết.

---

### Bước 2D — Tìm kiếm YouTube

```powershell
python "E:\Claude-Code\AutoMedia\scripts\video_helper.py" search "<từ khóa>" 5
```

Hiển thị kết quả:
```
#  Tiêu đề                    Thời lượng  Kênh
1  <title>                    MM:SS       <uploader>
...
```

Hỏi người dùng chọn video số mấy, sau đó tiếp tục **Bước 2A**.

---

### Bước 3 — Tóm tắt transcript

JSON trả về từ script gồm: `title`, `url`, `uploader`, `duration_seconds`, `transcript`, `language`, `method`.

Nếu có field `error` → thông báo lỗi và dừng.

Tạo tóm tắt bằng **tiếng Việt** theo template sau:

```
## [title]

**Nguồn:** [url hoặc file] | **Thời lượng:** [Xm Ys] | **Ngôn ngữ gốc:** [language]
**Kênh/Tác giả:** [uploader] | **Phương pháp:** [method]

---

### Nội dung chính
[2–3 câu mô tả tổng quan chủ đề video]

### Các điểm quan trọng
- [Điểm 1]
- [Điểm 2]
- [Điểm 3]
- ...

### Kết luận
[2–3 câu tóm tắt thông điệp chính]
```

---

### Bước 4 — Lưu file .txt

1. Tạo thư mục output nếu chưa có:
```powershell
New-Item -ItemType Directory -Force "summaries"
```

2. Đặt tên file: làm sạch `title` (xóa `\ / : * ? " < > |`, thay space → `_`, tối đa 60 ký tự) + `_YYYYMMDD_HHMMSS.txt`

3. Nội dung file — dùng template tại `summary_template.txt` cùng thư mục:

```
=== TÓM TẮT VIDEO ===
Ngày tóm tắt : {datetime}
Nguồn        : {url_or_file}
Kênh/Tác giả : {uploader}
Thời lượng   : {duration}
Ngôn ngữ gốc : {language}
Phương pháp  : {method}
Model Whisper: {model}

================================================================

{summary}

================================================================
=== TRANSCRIPT GỐC ===

{transcript}
```

4. Dùng tool **Write** để ghi file.
5. Thông báo: `Đã lưu: summaries/<tên_file>.txt`
