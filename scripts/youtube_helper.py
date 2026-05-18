"""
YouTube helper: search and fetch transcripts using youtube-transcript-api.
Falls back to yt-dlp + Whisper for videos without captions.

Usage:
  python youtube_helper.py search "<query>" [max_results]
  python youtube_helper.py transcribe "<url_or_id>" [whisper_model]
  python youtube_helper.py transcribe-local "<audio_file_path>" [whisper_model]
"""

import sys
import os
import json
import re
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "downloads")
COOKIE_ARGS = ["--cookies-from-browser", "chrome"]


def _out(obj: dict) -> None:
    sys.stdout.buffer.write(json.dumps(obj, ensure_ascii=False).encode("utf-8"))
    sys.stdout.buffer.write(b"\n")
    sys.stdout.buffer.flush()


def _extract_video_id(url_or_id: str) -> str:
    match = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", url_or_id)
    return match.group(1) if match else url_or_id


def search(query: str, max_results: int = 5) -> None:
    cmd = [
        "yt-dlp",
        f"ytsearch{max_results}:{query}",
        "--dump-json", "--flat-playlist",
        "--no-warnings", "--quiet",
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


def _fetch_transcript(video_id: str) -> tuple[str, str] | tuple[None, None]:
    """Fetch transcript via youtube-transcript-api. Returns (text, language) or (None, None)."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
    except ImportError:
        return None, None

    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # Prefer manual captions, then auto-generated; Vietnamese or English first
        for lang in ["vi", "en"]:
            try:
                t = transcript_list.find_transcript([lang])
                segments = t.fetch()
                text = " ".join(s.text for s in segments)
                return text, t.language_code
            except Exception:
                pass

        # Fallback: take whatever is available
        t = next(iter(transcript_list))
        segments = t.fetch()
        text = " ".join(s.text for s in segments)
        return text, t.language_code

    except (NoTranscriptFound, TranscriptsDisabled):
        return None, None
    except Exception:
        return None, None


def _fetch_metadata(url: str) -> dict:
    """Get video metadata via yt-dlp."""
    meta_cmd = ["yt-dlp", "--dump-json", "--no-warnings", "--quiet", *COOKIE_ARGS, url]
    result = subprocess.run(meta_cmd, capture_output=True)
    if result.returncode == 0 and result.stdout.strip():
        try:
            return json.loads(result.stdout.decode("utf-8", errors="replace").strip())
        except json.JSONDecodeError:
            pass
    return {}


def _whisper_transcribe(audio_path: str, model_name: str) -> tuple[str, str]:
    """Transcribe a local file with Whisper. Returns (text, language)."""
    try:
        import whisper
    except ImportError:
        _out({"error": "openai-whisper not installed. Run: pip install openai-whisper"})
        sys.exit(1)
    result = whisper.load_model(model_name).transcribe(audio_path, verbose=False)
    return result.get("text", "").strip(), result.get("language", "unknown")


def transcribe(url: str, model_name: str = "base") -> None:
    if not url.startswith("http"):
        url = f"https://www.youtube.com/watch?v={url}"

    video_id = _extract_video_id(url)

    # Step 1: try caption API (fast, no download)
    print("[1/2] Fetching transcript from YouTube captions...", file=sys.stderr)
    transcript_text, lang = _fetch_transcript(video_id)

    metadata = {}
    method = "caption_api"

    if transcript_text:
        print("[1/2] Captions found.", file=sys.stderr)
        print("[2/2] Fetching video metadata...", file=sys.stderr)
        metadata = _fetch_metadata(url)
        video_file = ""
    else:
        # Step 2: fall back to download + Whisper
        print("[1/2] No captions available. Downloading audio for Whisper...", file=sys.stderr)
        os.makedirs(DOWNLOADS_DIR, exist_ok=True)
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
            _out({"error": f"Download failed: {dl_result.stderr}"})
            sys.exit(1)

        audio_path = dl_result.stdout.strip().splitlines()[-1] if dl_result.stdout.strip() else None
        if not audio_path or not os.path.isfile(audio_path):
            audio_exts = (".m4a", ".mp3", ".opus", ".webm", ".ogg")
            files = [os.path.join(DOWNLOADS_DIR, f) for f in os.listdir(DOWNLOADS_DIR) if f.endswith(audio_exts)]
            audio_path = max(files, key=os.path.getmtime) if files else None

        if not audio_path:
            _out({"error": "Audio file not found after download"})
            sys.exit(1)

        print(f"[2/2] Transcribing with Whisper ({model_name})...", file=sys.stderr)
        transcript_text, lang = _whisper_transcribe(audio_path, model_name)
        metadata = _fetch_metadata(url)
        video_file = audio_path
        method = "whisper"

    _out({
        "title": metadata.get("title", "Unknown"),
        "url": url,
        "uploader": metadata.get("uploader", "Unknown"),
        "duration_seconds": metadata.get("duration", 0),
        "description": (metadata.get("description") or "")[:500],
        "video_file": video_file,
        "transcript": transcript_text,
        "language": lang,
        "method": method,
    })


def transcribe_local(file_path: str, model_name: str = "base") -> None:
    if not os.path.isfile(file_path):
        _out({"error": f"File not found: {file_path}"})
        sys.exit(1)
    print(f"Transcribing with Whisper ({model_name})...", file=sys.stderr)
    text, lang = _whisper_transcribe(file_path, model_name)
    _out({
        "title": os.path.basename(file_path),
        "url": "",
        "uploader": "",
        "duration_seconds": 0,
        "description": "",
        "video_file": file_path,
        "transcript": text,
        "language": lang,
        "method": "whisper",
    })


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
        transcribe_local(arg, sys.argv[3] if len(sys.argv) > 3 else "base")
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
