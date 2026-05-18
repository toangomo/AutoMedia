#!/usr/bin/env python3
"""
makeup_helper.py - Apply AI beauty makeup to portrait images using OpenAI gpt-image-2
"""

import sys
import os
import json
import io
import base64
import time
from pathlib import Path

SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
KEYRING_SERVICE = "automedia-makeup"
KEYRING_USER = "openai_api_key"

MAKEUP_STYLE_PROMPT = """Edit this female portrait photo to apply the following makeup style precisely:
- Fresh makeup style with light pink blush on the cheeks and a soft touch of blush on the tip of the nose
- Full lips with a glossy gradient pink lipstick for a radiant, youthful look
- Fair, smooth, white skin with a flawless finish
- Sweet Korean-style makeup with soft pink tones throughout
- The woman's face must be exactly like the reference image in the attached file. Do not alter the facial structure, eyes, nose, or mouth
- Preserve the person's original facial features, expression, pose, and background exactly
- Only enhance the makeup and skin — do not alter anything else in the photo
- Maintain the exact same dimensions, size, and aspect ratio as the original image"""


def _get_api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key
    try:
        import keyring
        key = keyring.get_password(KEYRING_SERVICE, KEYRING_USER)
        if key:
            return key
    except Exception:
        pass
    _err("API key chưa được lưu. Chạy: python makeup_helper.py setup <api_key>")


def _err(msg: str):
    print(json.dumps({"error": msg}))
    sys.exit(1)


def setup_api_key(api_key: str):
    """Lưu API key vào Windows Credential Manager."""
    try:
        import keyring
    except ImportError:
        _err("Thiếu package. Chạy: pip install keyring")
    keyring.set_password(KEYRING_SERVICE, KEYRING_USER, api_key)
    masked = api_key[:8] + "..." + api_key[-4:]
    print(json.dumps({
        "status": "success",
        "message": "API key đã lưu an toàn vào Windows Credential Manager",
        "key_preview": masked
    }))


def check_api_key():
    """Kiểm tra API key đã được cấu hình chưa."""
    from_env = bool(os.environ.get("OPENAI_API_KEY"))
    from_keyring = False
    try:
        import keyring
        from_keyring = bool(keyring.get_password(KEYRING_SERVICE, KEYRING_USER))
    except Exception:
        pass
    status = "OK" if (from_env or from_keyring) else "MISSING"
    source = "environment variable" if from_env else ("Windows Credential Manager" if from_keyring else "not found")
    print(json.dumps({"status": status, "source": source}))


def _select_api_size(width: int, height: int) -> str:
    """Chọn size API gần nhất với tỉ lệ ảnh gốc."""
    ratio = width / height
    if ratio > 1.2:
        return "1536x1024"   # ngang
    elif ratio < 0.83:
        return "1024x1536"   # dọc
    else:
        return "1024x1024"   # vuông


def _output_path(image_path: Path, output_dir: str | None) -> Path:
    suffix = image_path.suffix.lower()
    if suffix not in ('.jpg', '.jpeg', '.png', '.webp'):
        suffix = '.jpg'
    stem = image_path.stem
    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        return out / f"{stem}_makeup{suffix}"
    return image_path.parent / f"{stem}_makeup{suffix}"


def apply_makeup(image_path: str, output_dir: str | None = None) -> dict:
    """Apply makeup to a single portrait image."""
    try:
        from openai import OpenAI
        import PIL.Image
    except ImportError:
        return {"error": "Thiếu package. Chạy: pip install openai Pillow"}

    p = Path(image_path)
    if not p.exists():
        return {"error": f"File không tồn tại: {image_path}"}
    if p.suffix.lower() not in SUPPORTED_FORMATS:
        return {"error": f"Định dạng không hỗ trợ: {p.suffix}"}

    out_path = _output_path(p, output_dir)

    try:
        # Đọc ảnh gốc và lưu kích thước
        original = PIL.Image.open(p)
        orig_w, orig_h = original.size
        api_size = _select_api_size(orig_w, orig_h)

        # Chuyển sang RGBA PNG cho API
        if original.mode != 'RGBA':
            original = original.convert('RGBA')
        buf = io.BytesIO()
        original.save(buf, format='PNG')
        buf.seek(0)
        buf.name = p.stem + ".png"

        client = OpenAI(api_key=_get_api_key())

        response = client.images.edit(
            model="gpt-image-2",
            image=buf,
            prompt=MAKEUP_STYLE_PROMPT,
            n=1,
            size=api_size
        )

        image_data = base64.b64decode(response.data[0].b64_json)
        result_img = PIL.Image.open(io.BytesIO(image_data))

        # Giữ nguyên độ phân giải server trả về, không resize
        save_format = 'JPEG' if p.suffix.lower() in ('.jpg', '.jpeg') else 'PNG'
        if save_format == 'JPEG' and result_img.mode == 'RGBA':
            result_img = result_img.convert('RGB')
        result_img.save(str(out_path), format=save_format, quality=80)

        out_w, out_h = result_img.size
        return {
            "status": "success",
            "input": str(p),
            "output": str(out_path),
            "original_size": f"{orig_w}x{orig_h}",
            "output_size": f"{out_w}x{out_h}",
            "api_size": api_size
        }

    except Exception as e:
        return {"error": str(e), "input": str(image_path)}


def list_images(folder_path: str):
    """List all supported image files in a folder."""
    folder = Path(folder_path)
    if not folder.is_dir():
        _err(f"Không phải thư mục: {folder_path}")

    images = [
        str(f) for f in sorted(folder.iterdir())
        if f.is_file()
        and f.suffix.lower() in SUPPORTED_FORMATS
        and '_makeup' not in f.stem
    ]
    print(json.dumps({"images": images, "count": len(images)}))


def process_folder(folder_path: str, output_dir: str | None = None):
    """Process all portrait images in a folder."""
    folder = Path(folder_path)
    if not folder.is_dir():
        _err(f"Không phải thư mục: {folder_path}")

    images = [
        f for f in sorted(folder.iterdir())
        if f.is_file()
        and f.suffix.lower() in SUPPORTED_FORMATS
        and '_makeup' not in f.stem
    ]

    if not images:
        _err("Không tìm thấy ảnh nào trong thư mục")

    results = []
    for i, img_path in enumerate(images, 1):
        print(f"[{i}/{len(images)}] Đang xử lý: {img_path.name}", file=sys.stderr)
        result = apply_makeup(str(img_path), output_dir)
        results.append(result)
        if i < len(images):
            time.sleep(2)

    print(json.dumps({
        "results": results,
        "total": len(results),
        "success": sum(1 for r in results if r.get("status") == "success"),
        "failed": sum(1 for r in results if "error" in r)
    }))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        _err("Cách dùng: makeup_helper.py <check|setup|apply|list|folder> [args...]")

    cmd = sys.argv[1]

    if cmd == "check":
        check_api_key()
    elif cmd == "setup":
        if len(sys.argv) < 3:
            _err("Cách dùng: makeup_helper.py setup <api_key>")
        setup_api_key(sys.argv[2])
    elif cmd == "apply":
        if len(sys.argv) < 3:
            _err("Cách dùng: makeup_helper.py apply <image_path> [output_dir]")
        out = sys.argv[3] if len(sys.argv) > 3 else None
        print(json.dumps(apply_makeup(sys.argv[2], out)))
    elif cmd == "list":
        if len(sys.argv) < 3:
            _err("Cách dùng: makeup_helper.py list <folder_path>")
        list_images(sys.argv[2])
    elif cmd == "folder":
        if len(sys.argv) < 3:
            _err("Cách dùng: makeup_helper.py folder <folder_path> [output_dir]")
        out = sys.argv[3] if len(sys.argv) > 3 else None
        process_folder(sys.argv[2], out)
    else:
        _err(f"Lệnh không hợp lệ: {cmd}. Dùng: check | setup | apply | list | folder")
