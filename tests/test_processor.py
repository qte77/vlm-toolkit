"""Tests for vlm_toolkit.processor — resize and JPEG encoding helpers."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from vlm_toolkit.processor import resize_for_vlm, save_jpeg


class TestResizeForVLM:
    def test_no_resize_when_under_max(self) -> None:
        img = Image.new("RGB", (500, 400))
        result = resize_for_vlm(img, max_edge=768)
        assert result.size == (500, 400)

    def test_default_max_edge_is_768(self) -> None:
        img = Image.new("RGB", (1536, 768))
        assert resize_for_vlm(img).size == (768, 384)

    def test_resize_landscape_preserves_aspect(self) -> None:
        img = Image.new("RGB", (1920, 1080))  # 16:9 → 768:432
        result = resize_for_vlm(img, max_edge=768)
        assert result.size == (768, 432)

    def test_resize_portrait_preserves_aspect(self) -> None:
        img = Image.new("RGB", (600, 1200))  # 1:2
        result = resize_for_vlm(img, max_edge=768)
        assert result.size == (384, 768)

    def test_resize_square(self) -> None:
        img = Image.new("RGB", (1024, 1024))
        result = resize_for_vlm(img, max_edge=512)
        assert result.size == (512, 512)


class TestSaveJpeg:
    def test_returns_destination(self, tmp_path: Path) -> None:
        img = Image.new("RGB", (100, 100), color=(128, 64, 32))
        dest = tmp_path / "out.jpg"
        assert save_jpeg(img, dest) == dest
        assert dest.stat().st_size > 0

    def test_saved_file_is_valid_jpeg(self, tmp_path: Path) -> None:
        img = Image.new("RGB", (100, 100), color=(128, 64, 32))
        dest = tmp_path / "out.jpg"
        save_jpeg(img, dest)
        with Image.open(dest) as loaded:
            assert loaded.format == "JPEG"
            assert loaded.size == (100, 100)

    def test_converts_rgba_to_rgb(self, tmp_path: Path) -> None:
        """JPEG does not support alpha — the helper must convert."""
        img = Image.new("RGBA", (50, 50), color=(100, 100, 100, 255))
        dest = tmp_path / "out.jpg"
        save_jpeg(img, dest)
        with Image.open(dest) as loaded:
            assert loaded.mode == "RGB"

    def test_lower_quality_smaller_file(self, tmp_path: Path) -> None:
        # Reason: noise, not a solid colour — solid images compress identically.
        img = Image.effect_noise((200, 200), sigma=30).convert("RGB")
        high_q = tmp_path / "high.jpg"
        low_q = tmp_path / "low.jpg"
        save_jpeg(img, high_q, quality=95)
        save_jpeg(img, low_q, quality=30)
        assert low_q.stat().st_size < high_q.stat().st_size
