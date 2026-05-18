"""
YouTube helper: search, download video, and transcribe using yt-dlp + Whisper.
Usage:
  python youtube_helper.py search "<query>" [max_results]
  python youtube_helper.py transcribe "<url_or_id>" [whisper_model]
  python youtube_helper.py transcribe-local "<video_file_path>" [whisper_model]
"""

import sys
import os
import json
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "downloads")
COOKIE_ARGS = ["--cookies-from-browser", "chrome"]


def _out(obj: dict) -> None:
    sys.stdout.buffer.write(json.dumps(obj, ensure_ascii=False).encode("utf-8"))
    sys.stdout.buffer.write(b"\n")
    sys.stdout.buffer.flush()


def search(query: str, max_results: int = 5) -> None:
    cmd = [
        "yt-dlp",
        f"ytsearch{max_results}:{query}",
        "--dump-json",
        "--flat-playlist",
        "--no-warnings",
        "--quiet",
        *COOKIE_ARGS,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    videos = []
    for line in result.stdout.strip().splitlines():
        if not line:
            continue
        try:
            data = json.loads(line)
            duration = data.get("duration")
            duration_str = f"{int(duration)//60}:{int(duration)%60:02d}" if duration else "N/A"
            videos.append({
                "index": len(videos) + 1,
                "id": data.get("id", ""),
                "title": data.get("title", "Unknown"),
                "url": f"https://www.youtube.com/watch?v={data.get('id', '')}",
                "duration": duration_str,
                "uploader": data.get("uploader", "Unknown"),
            })
        except json.JSONDecodeError:
            continue
    print(json.dumps(videos, ensure_ascii=False, indent=2))


def download_video(url: str) -> tuple[str | None, dict]:
    """Download video to downloads/ folder. Returns (file_path, metadata)."""
    if not url.startswith("http"):
        url = f"https://www.youtube.com/watch?v={url}"

    os.makedirs(DOWNLOADS_DIR, exist_ok=True)

    # Get metadata
    meta_cmd = ["yt-dlp", "--dump-json", "--no-warnings", "--quiet", *COOKIE_ARGS, url]
    meta_result = subprocess.run(meta_cmd, capture_output=True)
    metadata = {}
    if meta_result.returncode == 0 and meta_result.stdout.strip():
        try:
            metadata = json.loads(meta_result.stdout.decode("utf-8", errors="replace").strip())
        except json.JSONDecodeError:
            pass

    # Download audio only — sufficient for transcription, much smaller than video
    output_template = os.path.join(DOWNLOADS_DIR, "%(upload_date)s_%(id)s_%(title).80s.%(ext)s")
    dl_cmd = [
        "yt-dlp", url,
        "-f", "bestaudio/best",
        "-x", "--audio-format", "m4a",
        "-o", output_template,
        "--no-warnings",
        "--print", "after_move:filepath",
        *COOKIE_ARGS,
    ]
    dl_result = subprocess.run(dl_cmd, capture_output=True, text=True, encoding="utf-8")
    if dl_result.returncode != 0:
        return None, metadata

    video_path = dl_result.stdout.strip().splitlines()[-1] if dl_result.stdout.strip() else None
    if not video_path or not os.path.isfile(video_path):
        # Fallback: find the newest audio file in downloads/
        audio_exts = (".m4a", ".mp3", ".opus", ".webm", ".ogg")
        files = [
            os.path.join(DOWNLOADS_DIR, f)
            for f in os.listdir(DOWNLOADS_DIR)
            if f.endswith(audio_exts)
        ]
        video_path = max(files, key=os.path.getmtime) if files else None

    return video_path, metadata


def transcribe_file(video_path: str, model_name: str, metadata: dict | None = None) -> None:
    """Transcribe a local video/audio file with Whisper and print JSON result."""
    if not os.path.isfile(video_path):
        _out({"error": f"File not found: {video_path}"})
        sys.exit(1)

    try:
        import whisper
    except ImportError:
        _out({"error": "openai-whisper not installed. Run: pip install openai-whisper"})
        sys.exit(1)

    whisper_result = whisper.load_model(model_name).transcribe(video_path, verbose=False)

    _out({
        "title": (metadata or {}).get("title", os.path.basename(video_path)),
        "url": (metadata or {}).get("webpage_url", ""),
        "uploader": (metadata or {}).get("uploader", "Unknown"),
        "duration_seconds": (metadata or {}).get("duration", 0),
        "description": ((metadata or {}).get("description") or "")[:500],
        "video_file": video_path,
        "transcript": whisper_result.get("text", "").strip(),
        "language": whisper_result.get("language", "unknown"),
    })


def transcribe(url: str, model_name: str = "base") -> None:
    """Download video from URL then transcribe it."""
    print(f"[1/2] Downloading video...", file=sys.stderr)
    video_path, metadata = download_video(url)
    if not video_path:
        _out({"error": "Download failed"})
        sys.exit(1)
    print(f"[1/2] Saved to: {video_path}", file=sys.stderr)
    print(f"[2/2] Transcribing with Whisper ({model_name})...", file=sys.stderr)
    transcribe_file(video_path, model_name, metadata)


def main():
    if len(sys.argv) < 3:
        print("Usage: python youtube_helper.py <search|transcribe|transcribe-local> <query_or_url_or_path> [options]")
        sys.exit(1)

    command, arg = sys.argv[1], sys.argv[2]

    if command == "search":
        search(arg, int(sys.argv[3]) if len(sys.argv) > 3 else 5)
    elif command == "transcribe":
        transcribe(arg, sys.argv[3] if len(sys.argv) > 3 else "base")
    elif command == "transcribe-local":
        # Transcribe an already-downloaded local file
        transcribe_file(arg, sys.argv[3] if len(sys.argv) > 3 else "base")
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
