"""Property-based tests for vlm_toolkit.processor (Hypothesis).

`max_examples` is capped so the module stays well under 1 s.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st
from PIL import Image

from vlm_toolkit.processor import resize_for_vlm, save_jpeg

FAST = settings(max_examples=40, deadline=None)

sizes = st.integers(min_value=1, max_value=4000)
edges = st.integers(min_value=16, max_value=1024)


@FAST
@given(width=sizes, height=sizes, max_edge=edges)
def test_resize_bounds_and_aspect(width: int, height: int, max_edge: int) -> None:
    # Reason: mode "1" keeps even 4000x4000 inputs tiny in memory.
    img = Image.new("1", (width, height))
    out_w, out_h = resize_for_vlm(img, max_edge=max_edge).size

    if max(width, height) <= max_edge:
        assert (out_w, out_h) == (width, height)
        return
    assert max(out_w, out_h) <= max_edge
    assert min(out_w, out_h) >= 1
    # Aspect ratio preserved within 1px on the shorter side.
    if width >= height:
        assert abs(out_h - height * out_w / width) <= 1
    else:
        assert abs(out_w - width * out_h / height) <= 1


rgb = st.tuples(*[st.integers(min_value=0, max_value=255)] * 3)
modes = st.sampled_from(["RGB", "RGBA", "L", "P"])


@FAST
@given(
    color=rgb,
    mode=modes,
    width=st.integers(min_value=1, max_value=64),
    height=st.integers(min_value=1, max_value=64),
    quality=st.integers(min_value=70, max_value=95),
)
def test_save_jpeg_round_trip(
    color: tuple[int, int, int], mode: str, width: int, height: int, quality: int
) -> None:
    # Reason: "P" conversion dithers by default, which would break "solid colour".
    src = Image.new("RGB", (width, height), color).convert(mode, dither=Image.Dither.NONE)
    expected = src.convert("RGB").getpixel((0, 0))
    assert isinstance(expected, tuple)

    with tempfile.TemporaryDirectory() as tmp:
        dest = save_jpeg(src, Path(tmp) / "out.jpg", quality=quality)
        with Image.open(dest) as loaded:
            assert loaded.format == "JPEG"
            assert loaded.mode == "RGB"
            assert loaded.size == (width, height)
            got = loaded.getpixel((width // 2, height // 2))
    assert isinstance(got, tuple)
    # Solid colour survives JPEG within a small quantisation tolerance.
    assert all(abs(g - e) <= 8 for g, e in zip(got, expected, strict=True))
