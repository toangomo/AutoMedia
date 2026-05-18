---
description: Tóm tắt nội dung video — hỗ trợ YouTube URL, file local, hoặc cả folder
argument-hint: <YouTube URL | đường dẫn file | đường dẫn folder> [--model base|small|medium|large]
allowed-tools: Bash, Read, Write
---

Tóm tắt nội dung video từ đầu vào: **$ARGUMENTS**

---

## Bước 1 — Phân tích đầu vào

Tách `$ARGUMENTS` thành:
- **`--model <tên>`** nếu có (base/small/medium/large). Mặc định: `base`.
- **Phần còn lại** là input chính, xác định loại:

| Loại | Nhận biết | Xử lý |
|------|-----------|-------|
| YouTube URL | chứa `youtube.com`, `youtu.be`, `shorts/` | Bước 3A |
| Folder | là đường dẫn thư mục tồn tại | Bước 3B |
| File local | là đường dẫn file tồn tại | Bước 3C |
| Từ khóa | không thuộc các loại trên | Bước 2 |

---

## Bước 2 — Tìm kiếm YouTube (chỉ khi input là từ khóa)

```powershell
python "E:\Claude-Code\AutoMedia\scripts\video_helper.py" search "<từ khóa>" 5
```

Hiển thị kết quả dạng bảng và hỏi người dùng chọn video số mấy.
Sau khi chọn, lấy URL rồi tiếp tục **Bước 3A**.

---

## Bước 3A — YouTube URL

```powershell
python "E:\Claude-Code\AutoMedia\scripts\video_helper.py" transcribe-youtube "<url>" <model>
```

Script tự động thử:
1. Lấy phụ đề từ YouTube caption API (nhanh, không bị chặn)
2. Nếu không có phụ đề → tải audio + Whisper (fallback)

Tiếp tục **Bước 4** với kết quả JSON.

---

## Bước 3B — Folder local

```powershell
python "E:\Claude-Code\AutoMedia\scripts\video_helper.py" list-videos "<folder_path>"
```

Script trả về danh sách đường dẫn file media trong folder.
Hiển thị danh sách cho người dùng xác nhận, rồi xử lý **từng file tuần tự**:

Với mỗi file, chạy **Bước 3C** → **Bước 4** → **Bước 5**.
Sau khi xong tất cả, báo cáo tổng kết số file đã xử lý.

---

## Bước 3C — File local

```powershell
python "E:\Claude-Code\AutoMedia\scripts\video_helper.py" transcribe-local "<file_path>" <model>
```

Tiếp tục **Bước 4** với kết quả JSON.

---

## Bước 4 — Tóm tắt nội dung

Dùng `transcript` từ JSON để tóm tắt bằng **tiếng Việt**:

```
## [Tiêu đề video]

**Nguồn:** [url hoặc tên file] | **Thời lượng:** [duration] | **Ngôn ngữ:** [language]

### Nội dung chính
[2-3 câu mô tả chủ đề]

### Các điểm quan trọng
- [Điểm 1]
- [Điểm 2]
- ...

### Kết luận
[2-3 câu tóm tắt kết luận]
```

---

## Bước 5 — Lưu file .txt

**Tên file:** làm sạch tiêu đề (bỏ ký tự đặc biệt, thay space bằng `_`) + timestamp `YYYYMMDD_HHMMSS` + `.txt`

**Thư mục:** `E:\Claude-Code\AutoMedia\summaries\`

**Nội dung file:**
```
=== TÓM TẮT VIDEO ===
Ngày: [datetime]
Nguồn: [url hoặc đường dẫn file]
Kênh/Tác giả: [uploader]
Thời lượng: [duration]
Ngôn ngữ: [language]
Phương pháp: [caption_api / whisper]
Model Whisper: [model hoặc N/A]

=============================

[Toàn bộ nội dung tóm tắt]

=============================
=== TRANSCRIPT GỐC ===

[Toàn bộ transcript]
```

Dùng **tool Write** để ghi file, sau đó thông báo đường dẫn đã lưu.

---

> **Ghi chú:**
> - Với **folder**: mỗi video tạo một file .txt riêng trong `summaries\`
> - **Model Whisper**: `base` đủ dùng cho đa số video; dùng `medium` cho tiếng Việt
> - Định dạng hỗ trợ: mp4, avi, mkv, mov, wmv, flv, webm, m4v, mp3, m4a, wav, ogg, opus, aac, flac
