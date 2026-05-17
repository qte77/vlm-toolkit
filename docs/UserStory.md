# UserStory — vlm-toolkit

Authority doc for `v0.1.0` acceptance. Mirrors the so101 convention.

## Roles

- **DownstreamAgent** — code in a consumer repo (`i3mega-pipettebot`, `so101-biolab-automation`, etc.) that imports `vlm_toolkit`.
- **ToolkitMaintainer** — owns `vlm-toolkit` API stability and releases.

## Stories

### US-1 — Describe an image with a GGUF VLM

As a **DownstreamAgent**, I can call `resolve_vlm_engine()` and pass a file path to get a short text description, regardless of whether the backend is in-process `llama-cpp-python` or HTTP `llama-server`.

**Acceptance:**

- `vlm_toolkit.resolve_vlm_engine("auto")` returns the first available engine.
- `engine.describe(image_path, prompt)` returns a non-empty `str` for any readable JPEG/PNG path.
- `engine.available()` returns `False` (not raises) when dependencies or model files are missing.
- Engine selection works with no kwargs *only* if env vars or `.toml` config are set; otherwise raises with a single actionable error message naming the missing setting.

### US-2 — Detect known objects with YOLO26

As a **DownstreamAgent**, I can call `resolve_detector()` and pass a file path to get a list of detections with `label`, `confidence`, `bbox`.

**Acceptance:**

- `vlm_toolkit.resolve_detector("ultralytics")` returns a `Detector` instance.
- `detector.detect(image_path)` returns `list[Detection]` (possibly empty); never raises on a valid image.
- Custom-trained `.pt` weights are loadable via the same factory by passing `weights_path=`.
- Confidence threshold is configurable per call.

### US-3 — Two-stage detect-then-describe

As a **DownstreamAgent**, I can wire a detector and a VLM together so the VLM only fires when one of my trigger labels is hit.

**Acceptance:**

- `DetectThenDescribe(detector, engine, trigger_labels, prompt).run(image_path)` returns `(detections, vlm_text_or_None)`.
- `vlm_text_or_None` is `None` iff no detection's label is in `trigger_labels`.
- A heartbeat mode (force VLM on every Nth frame regardless of trips) is exposed by a separate `heartbeat_every: int | None` constructor arg.

### US-4 — Capture stays my problem

As a **DownstreamAgent**, I bring my own frame source (USB cam / screen / RTSP / file). The toolkit never imports an OS-level capture library at the top level.

**Acceptance:**

- `import vlm_toolkit` succeeds with only the base deps installed; no implicit `mss`, `opencv-python`, `gst`, etc.
- All public functions accept a `Path` (and, after `v0.2`, `bytes`) — never a frame-source handle.

### US-5 — Mockable for offline tests

As a **DownstreamAgent**, I can write fast unit tests that don't load model files or pull torch.

**Acceptance:**

- `VLMEngine` and `Detector` are `Protocol`s — easy to satisfy with a hand-written fake.
- `vlm-toolkit`'s own test suite runs in under 10 seconds without any model file present.

### US-6 — Stable git-pinned dependency

As a **DownstreamAgent**, I can pin `vlm-toolkit` to a commit SHA and trust that minor releases keep the public API surface listed in `architecture.md §5`.

**Acceptance:**

- Public re-exports in `src/vlm_toolkit/__init__.py` are the *only* supported import path; everything else is `_private`.
- Breaking changes to the public surface bump the minor version (`0.x → 0.x+1`) while `0.x.y` is in effect; major bumps once `1.0.0` ships.
- `CHANGELOG.md` lists every public-API change.

## Out of scope for v0.1.0

- In-memory `bytes`/`numpy` input path (planned for `v0.2`).
- A `FrameSource` Protocol (revisit once consumer duplication is concrete).
- PyPI publishing (git-only).
- Claude Code plugin integration (`cc-senses-plugin` keeps its own `cc_vlm/`).
