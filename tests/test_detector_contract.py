"""Contract tests for vlm_toolkit.detector.

`ultralytics` (and torch) are never imported: a fake module exposing a
`YOLO` class is injected into `sys.modules`.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, ClassVar

import pytest

from vlm_toolkit.detector import (
    Detection,
    Detector,
    UltralyticsDetector,
    resolve_detector,
)


class _Tensor:
    """Minimal stand-in for a torch tensor: only `.tolist()` is used."""

    def __init__(self, values: list[Any]) -> None:
        self._values = values

    def tolist(self) -> list[Any]:
        return self._values


class FakeYOLO:
    instances: ClassVar[list[FakeYOLO]] = []

    def __init__(self, weights: str) -> None:
        self.weights = weights
        self.calls: list[dict[str, Any]] = []
        FakeYOLO.instances.append(self)

    def predict(self, source: str, conf: float, verbose: bool) -> list[Any]:
        self.calls.append({"source": source, "conf": conf, "verbose": verbose})
        boxes = SimpleNamespace(
            xyxy=_Tensor([[10.4, 20.6, 110.0, 220.9], [0.0, 0.0, 5.0, 5.0]]),
            cls=_Tensor([0.0, 2.0]),
            conf=_Tensor([0.91, 0.42]),
        )
        return [SimpleNamespace(boxes=boxes, names={0: "pipette", 2: "bubble"})]


@pytest.fixture
def fake_ultralytics(monkeypatch: pytest.MonkeyPatch) -> type[FakeYOLO]:
    FakeYOLO.instances = []
    monkeypatch.setitem(sys.modules, "ultralytics", SimpleNamespace(YOLO=FakeYOLO))
    return FakeYOLO


@pytest.fixture
def no_ultralytics(monkeypatch: pytest.MonkeyPatch) -> None:
    # Reason: a None entry in sys.modules makes `import ultralytics` raise ImportError.
    monkeypatch.setitem(sys.modules, "ultralytics", None)


class FakeDetector:
    """Protocol fake: proves the contract is satisfiable without ultralytics."""

    @property
    def name(self) -> str:
        return "fake"

    def available(self) -> bool:
        return True

    def detect(self, image_path: Path) -> list[Detection]:
        return [Detection(label="x", confidence=1.0, bbox=(0, 0, 1, 1))]


def test_fake_detector_satisfies_protocol() -> None:
    detector: Detector = FakeDetector()
    assert detector.detect(Path("img.jpg"))[0]["label"] == "x"


class TestUltralyticsDetector:
    def test_name(self) -> None:
        assert UltralyticsDetector().name == "ultralytics"

    def test_default_weights_is_yolo26n(self) -> None:
        assert UltralyticsDetector().weights_path == "yolo26n.pt"

    def test_available_with_ultralytics(self, fake_ultralytics: type[FakeYOLO]) -> None:
        assert UltralyticsDetector().available()

    def test_unavailable_without_ultralytics(self, no_ultralytics: None) -> None:
        assert not UltralyticsDetector().available()

    def test_available_does_not_load_model(self, fake_ultralytics: type[FakeYOLO]) -> None:
        UltralyticsDetector().available()
        assert fake_ultralytics.instances == []

    def test_detect_maps_results(self, fake_ultralytics: type[FakeYOLO]) -> None:
        detections = UltralyticsDetector().detect(Path("frame.jpg"))
        assert detections == [
            {"label": "pipette", "confidence": 0.91, "bbox": (10, 21, 110, 221)},
            {"label": "bubble", "confidence": 0.42, "bbox": (0, 0, 5, 5)},
        ]
        assert all(isinstance(v, int) for d in detections for v in d["bbox"])

    def test_detect_passes_source_and_default_conf(self, fake_ultralytics: type[FakeYOLO]) -> None:
        UltralyticsDetector(conf=0.3).detect(Path("frame.jpg"))
        assert fake_ultralytics.instances[0].calls == [
            {"source": "frame.jpg", "conf": 0.3, "verbose": False}
        ]

    def test_conf_override_per_call(self, fake_ultralytics: type[FakeYOLO]) -> None:
        UltralyticsDetector(conf=0.3).detect(Path("frame.jpg"), conf=0.7)
        assert fake_ultralytics.instances[0].calls[0]["conf"] == 0.7

    def test_model_loaded_once(self, fake_ultralytics: type[FakeYOLO]) -> None:
        detector = UltralyticsDetector(weights_path="custom.pt")
        detector.detect(Path("a.jpg"))
        detector.detect(Path("b.jpg"))
        assert [y.weights for y in fake_ultralytics.instances] == ["custom.pt"]

    def test_empty_result(
        self, fake_ultralytics: type[FakeYOLO], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        empty = SimpleNamespace(xyxy=_Tensor([]), cls=_Tensor([]), conf=_Tensor([]))
        monkeypatch.setattr(
            FakeYOLO, "predict", lambda *_a, **_k: [SimpleNamespace(boxes=empty, names={})]
        )
        assert UltralyticsDetector().detect(Path("a.jpg")) == []


class TestResolveDetector:
    def test_returns_ultralytics_detector(self, fake_ultralytics: type[FakeYOLO]) -> None:
        detector = resolve_detector("ultralytics")
        assert isinstance(detector, UltralyticsDetector)

    def test_default_engine_is_ultralytics(self, fake_ultralytics: type[FakeYOLO]) -> None:
        assert resolve_detector().name == "ultralytics"

    def test_forwards_weights_and_conf(self, fake_ultralytics: type[FakeYOLO]) -> None:
        detector = resolve_detector(weights_path="my.pt", conf=0.5)
        assert isinstance(detector, UltralyticsDetector)
        assert (detector.weights_path, detector.conf) == ("my.pt", 0.5)

    def test_unknown_engine(self) -> None:
        with pytest.raises(ValueError, match="Unknown detector"):
            resolve_detector("nope")

    def test_unavailable_raises_with_install_hint(self, no_ultralytics: None) -> None:
        with pytest.raises(RuntimeError, match=r"\[detector\]"):
            resolve_detector("ultralytics")
