"""
YouTube helper: search, download audio, and transcribe using yt-dlp + Whisper.
Usage:
  python youtube_helper.py search "<query>" [max_results]
  python youtube_helper.py transcribe "<url_or_id>" [whisper_model]
"""

import sys
import os
import json
import subprocess
import tempfile

COOKIE_ARGS = ["--cookies-from-browser", "chrome"]


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


def transcribe(url: str, model_name: str = "base") -> None:
    if not url.startswith("http"):
        url = f"https://www.youtube.com/watch?v={url}"

    def _out(obj):
        sys.stdout.buffer.write(json.dumps(obj, ensure_ascii=False).encode("utf-8"))
        sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()

    meta_cmd = ["yt-dlp", "--dump-json", "--no-warnings", "--quiet", *COOKIE_ARGS, url]
    meta_result = subprocess.run(meta_cmd, capture_output=True)
    metadata = {}
    if meta_result.returncode == 0 and meta_result.stdout.strip():
        try:
            metadata = json.loads(meta_result.stdout.decode("utf-8", errors="replace").strip())
        except json.JSONDecodeError:
            pass

    with tempfile.TemporaryDirectory() as tmp_dir:
        audio_path = os.path.join(tmp_dir, "audio.%(ext)s")
        dl_cmd = [
            "yt-dlp", url,
            "-x", "--audio-format", "mp3", "--audio-quality", "0",
            "-o", audio_path,
            "--no-warnings", "--quiet",
            *COOKIE_ARGS,
        ]
        dl_result = subprocess.run(dl_cmd, capture_output=True)
        if dl_result.returncode != 0:
            _out({"error": f"Download failed: {dl_result.stderr.decode('utf-8', errors='replace')}"})
            sys.exit(1)

        mp3_file = next(
            (os.path.join(tmp_dir, f) for f in os.listdir(tmp_dir) if f.endswith(".mp3")),
            None,
        )
        if not mp3_file:
            _out({"error": "Audio file not found after download"})
            sys.exit(1)

        try:
            import whisper
        except ImportError:
            _out({"error": "openai-whisper not installed. Run: pip install openai-whisper"})
            sys.exit(1)

        whisper_result = whisper.load_model(model_name).transcribe(mp3_file, verbose=False)

        _out({
            "title": metadata.get("title", "Unknown"),
            "url": url,
            "uploader": metadata.get("uploader", "Unknown"),
            "duration_seconds": metadata.get("duration", 0),
            "description": (metadata.get("description") or "")[:500],
            "transcript": whisper_result.get("text", "").strip(),
            "language": whisper_result.get("language", "unknown"),
        })


def main():
    if len(sys.argv) < 3:
        print("Usage: python youtube_helper.py <search|transcribe> <query_or_url> [options]")
        sys.exit(1)

    command, arg = sys.argv[1], sys.argv[2]

    if command == "search":
        search(arg, int(sys.argv[3]) if len(sys.argv) > 3 else 5)
    elif command == "transcribe":
        transcribe(arg, sys.argv[3] if len(sys.argv) > 3 else "base")
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
