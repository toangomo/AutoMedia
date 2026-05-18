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
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIES_JSON = os.path.join(SCRIPT_DIR, "www.youtube.com_cookies.json")
COOKIES_TXT = os.path.join(SCRIPT_DIR, "cookies.txt")


def build_cookies_txt() -> str | None:
    """Convert browser-exported JSON cookies to Netscape format for yt-dlp."""
    if not os.path.exists(COOKIES_JSON):
        return None
    with open(COOKIES_JSON, encoding="utf-8") as f:
        cookies = json.load(f)
    lines = ["# Netscape HTTP Cookie File\n"]
    for c in cookies:
        domain = c.get("domain", "")
        subdomains = "TRUE" if domain.startswith(".") else "FALSE"
        path = c.get("path", "/")
        secure = "TRUE" if c.get("secure", False) else "FALSE"
        expiry = int(c.get("expirationDate", 0))
        name = c.get("name", "")
        value = c.get("value", "")
        lines.append(f"{domain}\t{subdomains}\t{path}\t{secure}\t{expiry}\t{name}\t{value}\n")
    with open(COOKIES_TXT, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return COOKIES_TXT


def search(query: str, max_results: int = 5, cookies_path: str | None = None) -> None:
    cookie_args = ["--cookies", cookies_path] if cookies_path else []
    cmd = [
        "yt-dlp",
        f"ytsearch{max_results}:{query}",
        "--dump-json",
        "--flat-playlist",
        "--no-warnings",
        "--quiet",
        *cookie_args,
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


def transcribe(url: str, model_name: str = "base", cookies_path: str | None = None) -> None:
    # Normalize short IDs to full URL
    if not url.startswith("http"):
        url = f"https://www.youtube.com/watch?v={url}"

    # Build cookie args: prefer cookies.txt from JSON, then fall back to browser
    if cookies_path and os.path.isfile(cookies_path):
        cookie_args = ["--cookies", cookies_path]
    else:
        import platform
        cookie_args = []
        system = platform.system()
        browser_paths = []
        if system == "Windows":
            local = os.environ.get("LOCALAPPDATA", "")
            appdata = os.environ.get("APPDATA", "")
            browser_paths = [
                ("edge",    os.path.join(local, "Microsoft", "Edge", "User Data")),
                ("chrome",  os.path.join(local, "Google", "Chrome", "User Data")),
                ("firefox", os.path.join(appdata, "Mozilla", "Firefox", "Profiles")),
            ]
        elif system == "Darwin":
            home = os.path.expanduser("~")
            browser_paths = [
                ("chrome",  os.path.join(home, "Library", "Application Support", "Google", "Chrome")),
                ("firefox", os.path.join(home, "Library", "Application Support", "Firefox", "Profiles")),
            ]
        else:
            home = os.path.expanduser("~")
            browser_paths = [
                ("chrome",  os.path.join(home, ".config", "google-chrome")),
                ("firefox", os.path.join(home, ".mozilla", "firefox")),
            ]
        for browser, path in browser_paths:
            if os.path.isdir(path):
                cookie_args = ["--cookies-from-browser", browser]
                break

    def _out(obj):
        sys.stdout.buffer.write(json.dumps(obj, ensure_ascii=False).encode("utf-8"))
        sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()

    # Get video metadata first
    meta_cmd = ["yt-dlp", "--dump-json", "--no-warnings", "--quiet"] + cookie_args + [url]
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
            "yt-dlp",
            url,
            "-x",
            "--audio-format", "mp3",
            "--audio-quality", "0",
            "-o", audio_path,
            "--no-warnings",
            "--quiet",
        ] + cookie_args
        dl_result = subprocess.run(dl_cmd, capture_output=True)
        if dl_result.returncode != 0:
            err_msg = dl_result.stderr.decode("utf-8", errors="replace")
            _out({"error": f"Download failed: {err_msg}"})
            sys.exit(1)

        # Find the downloaded mp3
        mp3_file = None
        for f in os.listdir(tmp_dir):
            if f.endswith(".mp3"):
                mp3_file = os.path.join(tmp_dir, f)
                break

        if not mp3_file:
            _out({"error": "Audio file not found after download"})
            sys.exit(1)

        # Transcribe with Whisper
        try:
            import whisper
        except ImportError:
            _out({"error": "openai-whisper not installed. Run: pip install openai-whisper"})
            sys.exit(1)

        model = whisper.load_model(model_name)
        whisper_result = model.transcribe(mp3_file, verbose=False)

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

    command = sys.argv[1]
    arg = sys.argv[2]

    cookies_path = build_cookies_txt()

    if command == "search":
        max_results = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        search(arg, max_results, cookies_path)
    elif command == "transcribe":
        model_name = sys.argv[3] if len(sys.argv) > 3 else "base"
        transcribe(arg, model_name, cookies_path)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
