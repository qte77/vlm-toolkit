"""Object detector abstraction and the Ultralytics (YOLO26) implementation.

Mirrors the VLM engine's Protocol + resolver pattern. `ultralytics` pulls
torch, so it is an opt-in extra (`vlm-toolkit[detector]`) and is imported
lazily — `import vlm_toolkit.detector` stays light.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Protocol, TypedDict


class Detection(TypedDict):
    label: str
    confidence: float
    bbox: tuple[int, int, int, int]  # xyxy, pixels


class Detector(Protocol):
    """Protocol for object-detector backends."""

    def detect(self, image_path: Path) -> list[Detection]: ...

    def available(self) -> bool: ...

    @property
    def name(self) -> str: ...


def _import_ultralytics() -> Any:
    # Reason: import via importlib so strict pyright sees `Any`, not an
    # unresolved module, when the heavy [detector] extra is not installed.
    return importlib.import_module("ultralytics")


class UltralyticsDetector:
    """YOLO detector via `ultralytics.YOLO`.

    `weights_path` is any weights file `ultralytics.YOLO` accepts: a bare
    official name such as `yolo26n.pt` (downloaded by ultralytics on first
    use) or a path to custom-trained `.pt` weights. The model is loaded on
    the first `detect()` call and reused afterwards.
    """

    def __init__(self, weights_path: str = "yolo26n.pt", conf: float = 0.25) -> None:
        self.weights_path = weights_path
        self.conf = conf
        self._model: Any = None  # Lazily loaded ultralytics.YOLO instance.

    @property
    def name(self) -> str:
        return "ultralytics"

    def available(self) -> bool:
        """True iff `ultralytics` is importable. Does not load the model."""
        try:
            _import_ultralytics()
        except ImportError:
            return False
        return True

    def _load(self) -> Any:
        if self._model is None:
            self._model = _import_ultralytics().YOLO(self.weights_path)
        return self._model

    def detect(self, image_path: Path, conf: float | None = None) -> list[Detection]:
        """Run the detector on one image.

        `conf` overrides the instance confidence threshold for this call.
        Returns an empty list when nothing is detected.
        """
        results = self._load().predict(
            source=str(image_path),
            conf=self.conf if conf is None else conf,
            verbose=False,
        )
        detections: list[Detection] = []
        for result in results:
            boxes = result.boxes
            names: dict[int, str] = result.names
            for xyxy, cls_id, score in zip(
                boxes.xyxy.tolist(), boxes.cls.tolist(), boxes.conf.tolist(), strict=True
            ):
                x1, y1, x2, y2 = (round(v) for v in xyxy)
                detections.append(
                    Detection(
                        label=names[int(cls_id)],
                        confidence=float(score),
                        bbox=(x1, y1, x2, y2),
                    )
                )
        return detections


_DETECTOR_TYPES: dict[str, type[UltralyticsDetector]] = {"ultralytics": UltralyticsDetector}


def resolve_detector(
    engine_name: str = "ultralytics",
    *,
    weights_path: str = "yolo26n.pt",
    conf: float = 0.25,
) -> Detector:
    """Build a detector by name; raise if it is unknown or unavailable."""
    cls = _DETECTOR_TYPES.get(engine_name)
    if cls is None:
        msg = f"Unknown detector: {engine_name}. Available: {', '.join(_DETECTOR_TYPES)}"
        raise ValueError(msg)
    detector = cls(weights_path=weights_path, conf=conf)
    if not detector.available():
        msg = (
            "ultralytics not installed. Install the [detector] extra: "
            "`pip install 'vlm-toolkit[detector]'` (pulls torch)."
        )
        raise RuntimeError(msg)
    return detector
