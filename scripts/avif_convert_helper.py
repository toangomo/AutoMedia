#!/usr/bin/env python3
"""AVIF Convert Helper — converts images to AVIF format using Pillow."""

import sys
import json
import os
from pathlib import Path

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif', '.gif'}
DEFAULT_QUALITY = 80
SUBFOLDER_NAME = 'avif'


def _try_register_avif():
    try:
        import pillow_avif  # noqa: F401
    except ImportError:
        pass


def _check_avif_encode():
    import io
    from PIL import Image
    _try_register_avif()
    img = Image.new('RGB', (1, 1), color=(128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, format='AVIF', quality=80)
    return True


def cmd_check():
    try:
        _check_avif_encode()
        print(json.dumps({"status": "OK", "backend": "Pillow+AVIF"}))
    except Exception as e:
        print(json.dumps({
            "status": "MISSING",
            "error": str(e),
            "hint": "Run: pip install pillow pillow-avif-plugin"
        }))


def _convert_one(src: Path, out_dir: Path, quality: int) -> dict:
    from PIL import Image
    _try_register_avif()

    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / (src.stem + '.avif')

    with Image.open(src) as img:
        orig_size = img.size
        if img.mode in ('RGBA', 'LA', 'PA'):
            img = img.convert('RGBA')
        elif img.mode == 'P':
            # Palette with possible transparency
            img = img.convert('RGBA')
        else:
            img = img.convert('RGB')
        img.save(dest, format='AVIF', quality=quality)

    src_bytes = src.stat().st_size
    dest_bytes = dest.stat().st_size
    ratio = round((1 - dest_bytes / src_bytes) * 100, 1) if src_bytes else 0

    return {
        "status": "success",
        "input": str(src),
        "output": str(dest),
        "dimensions": f"{orig_size[0]}x{orig_size[1]}",
        "src_bytes": src_bytes,
        "dest_bytes": dest_bytes,
        "compression": f"{ratio}%"
    }


def cmd_convert(args):
    if not args:
        print(json.dumps({"status": "error", "error": "No file path provided"}))
        return
    src = Path(args[0])
    if not src.exists():
        print(json.dumps({"status": "error", "error": f"File not found: {src}"}))
        return
    if src.suffix.lower() not in IMAGE_EXTENSIONS:
        print(json.dumps({"status": "error", "error": f"Unsupported format: {src.suffix}"}))
        return

    # Default output: same folder as source
    out_dir = Path(args[1]) if len(args) > 1 else src.parent
    quality = int(args[2]) if len(args) > 2 else DEFAULT_QUALITY

    try:
        result = _convert_one(src, out_dir, quality)
    except Exception as e:
        result = {"status": "error", "input": str(src), "error": str(e)}
    print(json.dumps(result, ensure_ascii=False))


def cmd_list(args):
    if not args:
        print(json.dumps({"status": "error", "error": "No folder path provided"}))
        return
    folder = Path(args[0])
    if not folder.is_dir():
        print(json.dumps({"status": "error", "error": f"Not a directory: {folder}"}))
        return

    files = sorted(
        f for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    )
    total_bytes = sum(f.stat().st_size for f in files)
    print(json.dumps({
        "status": "OK",
        "folder": str(folder),
        "count": len(files),
        "total_size_kb": round(total_bytes / 1024, 1),
        "files": [f.name for f in files]
    }, ensure_ascii=False))


def cmd_folder(args):
    if not args:
        print(json.dumps({"status": "error", "error": "No folder path provided"}))
        return
    src_folder = Path(args[0])
    if not src_folder.is_dir():
        print(json.dumps({"status": "error", "error": f"Not a directory: {src_folder}"}))
        return

    out_dir = Path(args[1]) if len(args) > 1 else src_folder / SUBFOLDER_NAME
    quality = int(args[2]) if len(args) > 2 else DEFAULT_QUALITY

    files = sorted(
        f for f in src_folder.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    )

    results = []
    for i, f in enumerate(files, 1):
        print(f"[{i}/{len(files)}] Converting: {f.name}", file=sys.stderr, flush=True)
        try:
            r = _convert_one(f, out_dir, quality)
        except Exception as e:
            r = {"status": "error", "input": str(f), "error": str(e)}
        results.append(r)

    ok = [r for r in results if r.get("status") == "success"]
    total_src = sum(r.get("src_bytes", 0) for r in ok)
    total_dest = sum(r.get("dest_bytes", 0) for r in ok)
    overall = round((1 - total_dest / total_src) * 100, 1) if total_src else 0

    print(json.dumps({
        "status": "done",
        "total": len(files),
        "success": len(ok),
        "failed": len(files) - len(ok),
        "output_dir": str(out_dir),
        "overall_compression": f"{overall}%",
        "results": results
    }, ensure_ascii=False))


def cmd_setup():
    import subprocess
    print("Installing pillow and pillow-avif-plugin...", file=sys.stderr)
    r = subprocess.run(
        [sys.executable, '-m', 'pip', 'install', 'pillow', 'pillow-avif-plugin'],
        capture_output=True, text=True
    )
    if r.returncode == 0:
        print(json.dumps({"status": "OK", "message": "Packages installed successfully"}))
    else:
        print(json.dumps({"status": "error", "error": r.stderr[-500:]}))


COMMANDS = {
    'check': lambda args: cmd_check(),
    'convert': cmd_convert,
    'list': cmd_list,
    'folder': cmd_folder,
    'setup': lambda args: cmd_setup(),
}

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: avif_convert_helper.py <command> [args...]"}))
        sys.exit(1)
    cmd = sys.argv[1]
    args_rest = sys.argv[2:]
    if cmd not in COMMANDS:
        print(json.dumps({"error": f"Unknown command: {cmd}. Valid: {list(COMMANDS)}"}))
        sys.exit(1)
    COMMANDS[cmd](args_rest)
