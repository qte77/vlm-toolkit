# Architecture — vlm-toolkit

Draft. Subject to change before the `v0.1.0` tag.

## 1. Purpose

A small, branding-neutral Python library providing the two primitives both robotics consumers in the qte77 family need:

1. **YOLO26 detector** — fast, edge-friendly object detection for known failure classes / regions of interest.
2. **GGUF VLM describer** — image → short text, via `llama-cpp-python` (in-process) or `llama-server` (HTTP).

Plus a thin **pipeline glue** that runs the detector and only fires the VLM when the detector trips, to keep VLM token cost down on long-running camera loops.

The library does **not** ship a frame-source abstraction. Each consumer owns its own capture path (USB cam, OpenCV, screen grab, etc.) and passes a file `Path` (or bytes, post-`v0.1`) to the engine.

## 2. Scope

**In scope:**

- `Detector` Protocol + `UltralyticsDetector` reference implementation (YOLO26 family).
- `VLMEngine` Protocol + `LlamaCppVLMEngine` (in-process) and `LlamaServerVLMEngine` (HTTP).
- Image preprocessing (`resize_for_vlm`, `save_jpeg`).
- GGUF model registry (`models.toml`).
- `DetectThenDescribe` pipeline helper.
- `server_manager` for lazy `llama-server` lifecycle on localhost.

**Out of scope:**

- Frame capture (screen, USB, RTSP, GStreamer) — consumer-owned.
- Claude Code plugin coupling — `cc-senses-plugin` is intentionally **not** a consumer of this toolkit at `v0.1.0`. It keeps its own `cc_vlm/` module.
- Higher-level orchestration (failure-taxonomy, abort-vs-log policy, HITL alerts) — that lives in each consumer's domain code.

## 3. Locked decisions

| ID  | Question                          | Decision                                                                                 |
|-----|-----------------------------------|------------------------------------------------------------------------------------------|
| D1  | Repo name                         | `qte77/vlm-toolkit` — branding-neutral.                                                  |
| D2  | YOLO included?                    | Yes, behind `[detector]` extras (pulls torch — opt-in).                                  |
| D3  | Frame-source abstraction?         | No, for `v0.1`. Revisit if duplicate capture code appears across consumers.              |
| D4  | License                           | Apache-2.0.                                                                              |
| D5  | Python target                     | `>=3.11,<3.13`. Cap is forced by downstream VTK transitive (no cp313 wheels).            |
| D6  | Distribution                      | Git dep pinned to commit SHA. PyPI release deferred until API stabilises.                |
| D7  | `cc-senses-plugin` migration       | Out of scope. Toolkit is a parallel codebase, not a replacement.                          |
| D8  | `main` branch protection          | Enabled. See `§8`.                                                                       |

## 4. Repo layout

```text
vlm-toolkit/
├── README.md                          # minimal: tagline, consumers, link to docs/
├── LICENSE                            # Apache-2.0
├── CHANGELOG.md
├── pyproject.toml                     # hatchling; mirrors cc-senses pattern
├── src/vlm_toolkit/
│   ├── __init__.py                    # public re-exports
│   ├── engine.py                      # VLMEngine Protocol + LlamaCpp/LlamaServer impls
│   ├── detector.py                    # Detector Protocol + UltralyticsDetector
│   ├── processor.py                   # resize_for_vlm, save_jpeg
│   ├── pipeline.py                    # DetectThenDescribe
│   ├── server_manager.py              # llama-server lifecycle
│   └── models.toml                    # GGUF + YOLO model registry
├── tests/
│   ├── test_engine_contract.py        # mocked llama backends
│   ├── test_detector_contract.py      # mocked ultralytics
│   ├── test_processor.py
│   └── test_pipeline.py
└── docs/
    ├── architecture.md                # this file (AUTHORITY)
    ├── UserStory.md                   # acceptance criteria (AUTHORITY)
    └── consumers.md                   # i3 + so101 integration drafts
```

## 5. Public API (target for `v0.1.0`)

```python
from vlm_toolkit import (
    VLMEngine,            # Protocol
    resolve_vlm_engine,   # factory: "auto" | "llamacpp" | "llamaserver"
    Detector,             # Protocol
    resolve_detector,     # factory: "ultralytics"
    resize_for_vlm,
    save_jpeg,
)
from vlm_toolkit.pipeline import DetectThenDescribe
```

**Engine contract:**

```python
class VLMEngine(Protocol):
    def describe(self, image_path: Path, prompt: str) -> str: ...
    def available(self) -> bool: ...
    @property
    def name(self) -> str: ...
```

**Detector contract:**

```python
class Detection(TypedDict):
    label: str
    confidence: float
    bbox: tuple[int, int, int, int]   # xyxy

class Detector(Protocol):
    def detect(self, image_path: Path) -> list[Detection]: ...
    def available(self) -> bool: ...
    @property
    def name(self) -> str: ...
```

**Pipeline contract:**

```python
class DetectThenDescribe:
    def __init__(
        self,
        detector: Detector,
        engine: VLMEngine,
        trigger_labels: set[str],
        prompt: str,
    ) -> None: ...

    def run(self, image_path: Path) -> tuple[list[Detection], str | None]:
        """Detect; if any detection.label ∈ trigger_labels, call engine.describe.

        Returns (detections, vlm_text_or_None).
        """
```

## 6. Dependencies & extras

| Group          | Packages                                       | Notes                                          |
|----------------|------------------------------------------------|------------------------------------------------|
| core           | `pydantic-settings`, `Pillow`, `blake3`        | Always installed.                              |
| `[llamacpp]`   | (none direct — `llama-cpp-python` user-installed) | Hardware-specific wheel; toolkit detects.    |
| `[llamaserver]`| `httpx`                                        | HTTP client for `llama-server`.                |
| `[detector]`   | `ultralytics`                                  | Pulls torch — heavy, opt-in.                   |
| `[dev]`        | `ruff`, `pyright`, `bump-my-version`           |                                                |
| `[test]`       | `pytest`, `pytest-cov`, `hypothesis`           |                                                |
| `[all]`        | union of above runtime groups                  |                                                |

`llama-cpp-python` is intentionally **not** in `[llamacpp]` — same rationale as `cc-senses-plugin`: users install the variant matching their hardware (CPU / CUDA / Metal / ROCm).

## 7. Versioning & distribution

- `bump-my-version` config mirrors `cc-senses-plugin/pyproject.toml` (single-file version bumps, tag `v{new_version}`, no dirty commits).
- Releases: tag-based. `v0.x.y` while API is unstable; `v1.0.0` only after both downstream consumers have shipped against the toolkit and the API has held for ≥ one release cycle.
- Consumers pin to **commit SHA**, never to branch or tag-range. Mirrors `i3mega-pipettebot`'s `dpette @ git+...@<sha>` discipline.

## 8. Branch protection for `main`

To apply once the repo has its first commit on `main` (cannot protect a non-existent branch). Configure under **Settings → Branches → Add rule** or via `gh api`. Settings:

- **Require a pull request before merging:** on.
  - **Required approvals:** 1 (raise to 2 once additional reviewers are added).
  - **Dismiss stale pull request approvals when new commits are pushed:** on.
  - **Require review from Code Owners:** on once `CODEOWNERS` is added.
- **Require status checks to pass before merging:** on.
  - Required checks (once CI is wired): `ci / lint`, `ci / type-check`, `ci / test`.
  - **Require branches to be up to date before merging:** on.
- **Require conversation resolution before merging:** on.
- **Require signed commits:** on (matches qte77 convention; verify the user signs).
- **Require linear history:** on. (Pairs with squash-merge.)
- **Restrict who can push to matching branches:** on, empty allowlist (no direct pushes; everything via PR).
- **Allow force pushes:** off.
- **Allow deletions:** off.
- **Lock branch:** off.
- **Do not allow bypassing the above settings:** on, even for repo admins.
- **Merge button:** **Squash and merge only** (set under Settings → General → Pull Requests). Mirrors `i3mega-pipettebot` branch protection (`AGENTS.md` rule 5: "Topical commits with squash-merge").

## 9. Bootstrap sequence

Drafts only — no execution yet.

1. **Create the empty GitHub repo:**

   ```bash
   gh repo create qte77/vlm-toolkit \
     --public \
     --license Apache-2.0 \
     --description "Local GGUF VLM + small-object detector for headless robotics" \
     --homepage "https://github.com/qte77/vlm-toolkit"
   ```

2. Clone into `~/repos/qte77/vlm-toolkit/`. Replace the GitHub-generated `README.md` with the draft in this directory.
3. Land an initial scaffold PR on a `feat/initial-scaffold` branch: `pyproject.toml` + empty `src/vlm_toolkit/__init__.py` + `tests/` placeholder + `LICENSE` + this `docs/`. CI is added in this PR or the next.
4. Apply branch protection (`§8`) after the scaffold PR is squash-merged to `main`.
5. Subsequent PRs lift `engine.py` / `processor.py` / `server_manager.py` from `cc-senses-plugin` (Apache-2.0 → Apache-2.0, fine to copy with attribution in `NOTICE`). Add `detector.py` and `pipeline.py` from scratch.

## 10. Open items

- Owner / maintainer list for `CODEOWNERS`.
- CI provider: GitHub Actions assumed (matches family); confirm if otherwise.
- Whether to publish to PyPI at all, or stay git-only indefinitely. Default: git-only until API stabilises.
- Model registry contents — initial seed: `moondream`, `smolvlm`, `qwen3vl` (VLM, from `cc-senses-plugin/src/cc_vlm/models.toml`) + `yolo26n`, `yolo26s` (detector). Final list deferred until consumers pick.
