"""
Video helper: transcribe video/audio files or YouTube URLs.

Commands:
  python video_helper.py search <query> [max_results]
  python video_helper.py transcribe-youtube <url> [whisper_model]
  python video_helper.py transcribe-local <file_path> [whisper_model]
  python video_helper.py list-videos <folder_path>
"""

import sys
import os
import json
import re
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIE_ARGS = ["--cookies-from-browser", "chrome"]

MEDIA_EXTS = {
    ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".ts",
    ".mp3", ".m4a", ".wav", ".ogg", ".opus", ".aac", ".wma", ".flac",
}


def _out(obj: dict) -> None:
    sys.stdout.buffer.write(json.dumps(obj, ensure_ascii=False).encode("utf-8"))
    sys.stdout.buffer.write(b"\n")
    sys.stdout.buffer.flush()


def _whisper(file_path: str, model_name: str) -> tuple[str, str]:
    try:
        import whisper
    except ImportError:
        _out({"error": "openai-whisper not installed. Run: pip install openai-whisper"})
        sys.exit(1)
    result = whisper.load_model(model_name).transcribe(file_path, verbose=False)
    return result.get("text", "").strip(), result.get("language", "unknown")


def _extract_video_id(url: str) -> str | None:
    match = re.search(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})", url)
    return match.group(1) if match else None


def _fetch_yt_captions(video_id: str) -> tuple[str, str] | tuple[None, None]:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
    except ImportError:
        return None, None
    try:
        tlist = YouTubeTranscriptApi.list_transcripts(video_id)
        for lang in ["vi", "en"]:
            try:
                t = tlist.find_transcript([lang])
                text = " ".join(s.text for s in t.fetch())
                return text, t.language_code
            except Exception:
                pass
        t = next(iter(tlist))
        text = " ".join(s.text for s in t.fetch())
        return text, t.language_code
    except (NoTranscriptFound, TranscriptsDisabled):
        return None, None
    except Exception:
        return None, None


def _yt_metadata(url: str) -> dict:
    cmd = ["yt-dlp", "--dump-json", "--no-warnings", "--quiet", *COOKIE_ARGS, url]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode == 0 and r.stdout.strip():
        try:
            return json.loads(r.stdout.decode("utf-8", errors="replace").strip())
        except json.JSONDecodeError:
            pass
    return {}


# ── Commands ──────────────────────────────────────────────────────────────────

def search(query: str, max_results: int = 5) -> None:
    cmd = [
        "yt-dlp", f"ytsearch{max_results}:{query}",
        "--dump-json", "--flat-playlist", "--no-warnings", "--quiet",
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
            videos.append({
                "index": len(videos) + 1,
                "id": data.get("id", ""),
                "title": data.get("title", "Unknown"),
                "url": f"https://www.youtube.com/watch?v={data.get('id', '')}",
                "duration": f"{int(duration)//60}:{int(duration)%60:02d}" if duration else "N/A",
                "uploader": data.get("uploader", "Unknown"),
            })
        except json.JSONDecodeError:
            continue
    print(json.dumps(videos, ensure_ascii=False, indent=2))


def transcribe_youtube(url: str, model_name: str = "base") -> None:
    video_id = _extract_video_id(url)

    # Try captions first
    if video_id:
        print("[1/2] Fetching YouTube captions...", file=sys.stderr)
        text, lang = _fetch_yt_captions(video_id)
        if text:
            print("[2/2] Fetching metadata...", file=sys.stderr)
            meta = _yt_metadata(url)
            _out({
                "source": "youtube",
                "method": "caption_api",
                "title": meta.get("title", "Unknown"),
                "url": url,
                "uploader": meta.get("uploader", "Unknown"),
                "duration_seconds": meta.get("duration", 0),
                "description": (meta.get("description") or "")[:500],
                "file": "",
                "transcript": text,
                "language": lang,
            })
            return

    # Fall back to Whisper
    print("[1/2] No captions. Fetching metadata + downloading audio...", file=sys.stderr)
    meta = _yt_metadata(url)

    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        out_tpl = os.path.join(tmp, "audio.%(ext)s")
        dl = subprocess.run([
            "yt-dlp", url, "-f", "bestaudio/best",
            "-x", "--audio-format", "m4a",
            "-o", out_tpl, "--no-warnings", "--quiet",
            *COOKIE_ARGS,
        ], capture_output=True)
        if dl.returncode != 0:
            _out({"error": f"Download failed: {dl.stderr.decode('utf-8', errors='replace')}"})
            sys.exit(1)

        audio = next((os.path.join(tmp, f) for f in os.listdir(tmp) if f.endswith(".m4a")), None)
        if not audio:
            _out({"error": "Audio file not found after download"})
            sys.exit(1)

        print(f"[2/2] Transcribing with Whisper ({model_name})...", file=sys.stderr)
        text, lang = _whisper(audio, model_name)

    _out({
        "source": "youtube",
        "method": "whisper",
        "title": meta.get("title", "Unknown"),
        "url": url,
        "uploader": meta.get("uploader", "Unknown"),
        "duration_seconds": meta.get("duration", 0),
        "description": (meta.get("description") or "")[:500],
        "file": "",
        "transcript": text,
        "language": lang,
    })


def transcribe_local(file_path: str, model_name: str = "base") -> None:
    if not os.path.isfile(file_path):
        _out({"error": f"File not found: {file_path}"})
        sys.exit(1)
    print(f"Transcribing {os.path.basename(file_path)} with Whisper ({model_name})...", file=sys.stderr)
    text, lang = _whisper(file_path, model_name)
    _out({
        "source": "local",
        "method": "whisper",
        "title": os.path.splitext(os.path.basename(file_path))[0],
        "url": "",
        "uploader": "",
        "duration_seconds": 0,
        "description": "",
        "file": file_path,
        "transcript": text,
        "language": lang,
    })


def list_videos(folder_path: str) -> None:
    if not os.path.isdir(folder_path):
        _out({"error": f"Folder not found: {folder_path}"})
        sys.exit(1)
    files = sorted(
        os.path.join(folder_path, f)
        for f in os.listdir(folder_path)
        if os.path.splitext(f)[1].lower() in MEDIA_EXTS
    )
    print(json.dumps(files, ensure_ascii=False, indent=2))


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    command, arg = sys.argv[1], sys.argv[2]

    if command == "search":
        search(arg, int(sys.argv[3]) if len(sys.argv) > 3 else 5)
    elif command == "transcribe-youtube":
        transcribe_youtube(arg, sys.argv[3] if len(sys.argv) > 3 else "base")
    elif command == "transcribe-local":
        transcribe_local(arg, sys.argv[3] if len(sys.argv) > 3 else "base")
    elif command == "list-videos":
        list_videos(arg)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
