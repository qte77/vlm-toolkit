"""Image processing: resize and JPEG encoding for VLM input.

Lifted from cc-senses-plugin `src/cc_vlm/processor.py` (Apache-2.0, see NOTICE).
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image


def resize_for_vlm(img: Image.Image, max_edge: int = 768) -> Image.Image:
    """Resize image so its longest edge does not exceed max_edge pixels.

    Uses LANCZOS resampling for quality. Aspect ratio preserved. If the
    image is already smaller than max_edge, returns it unchanged.
    """
    width, height = img.size
    longest = max(width, height)
    if longest <= max_edge:
        return img
    scale = max_edge / longest
    new_size = (int(width * scale), int(height * scale))
    # Reason: Pillow's `size` annotation includes a numpy array type that is
    # Unknown when numpy is absent; our argument is a plain tuple[int, int].
    return img.resize(new_size, Image.Resampling.LANCZOS)  # pyright: ignore[reportUnknownMemberType]


def save_jpeg(img: Image.Image, dest: Path, quality: int = 85) -> Path:
    """Save PIL Image as JPEG at dest. Returns the dest path.

    Converts mode to RGB if needed (JPEG does not support RGBA). Uses
    optimize=True for smaller file size without quality loss.
    """
    if img.mode != "RGB":
        img = img.convert("RGB")
    img.save(dest, "JPEG", quality=quality, optimize=True)
    return dest
