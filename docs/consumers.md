# Consumers — vlm-toolkit

Draft integration plans for the two known downstream consumers. Each section ends with the **draft ADR text** to be copied into that consumer's `docs/adr/` when the consumer is ready to adopt the toolkit. ADRs are owned by their respective repos; this file is the upstream-side mirror so the toolkit knows who depends on it.

Cross-references to upstreams:

- [`qte77/i3mega-pipettebot`](https://github.com/qte77/i3mega-pipettebot)
- [`qte77/so101-biolab-automation`](https://github.com/qte77/so101-biolab-automation)

---

## A. i3mega-pipettebot

**Use case:** Overhead USB camera over the i3 Mega print bed. YOLO26n detects pipetting failure classes (missed wells, no tip, droplet on shaft, foam, spills). GGUF VLM fires on detector trip or heartbeat and produces a short text description, fed back into Claude Code context for diagnosis. See the `vlm-overhead-cam-on-rpi-research` conversation for background and the Pi feasibility table.

**New module:** `src/pipettebot/vision/`

```text
src/pipettebot/vision/
├── __init__.py
├── usb_capture.py     # OpenCV USB-webcam wrapper → PIL.Image → JPEG path
├── anomaly.py         # composes vlm_toolkit.DetectThenDescribe for pipetting classes
└── failure_modes.py   # taxonomy: missed_well | no_tip | droplet_on_shaft | foam | spill
```

**`pyproject.toml` change (consumer side):**

```toml
dependencies = [
    "pyserial>=3.5,<4",
    "dpette @ git+https://github.com/Lambda-Biolab/dpette-usb-driver.git@<sha>",
]

[project.optional-dependencies]
vision = [
    "vlm-toolkit[llamacpp,detector] @ git+https://github.com/qte77/vlm-toolkit.git@<sha>",
    "opencv-python>=4.10",
]
```

Vision is opt-in via `uv sync --extra vision` and never blocks `make validate` on machines without a camera or model files.

**Python target alignment:** pipettebot is `>=3.11,<3.13` and vlm-toolkit is `>=3.11,<3.13`. Compatible.

**Hardware test marker:** Reuse the existing `@pytest.mark.hardware` marker for any camera-dependent test. Unit tests mock `vlm_toolkit.Detector` and `vlm_toolkit.VLMEngine` via their Protocols.

**Pi runtime choice — to decide in the ADR:**

| Option                        | Latency       | Pi 5 (8 GB)        | Notes                                       |
|-------------------------------|---------------|--------------------|---------------------------------------------|
| On-Pi `LlamaCppVLMEngine`     | 2–5 s/frame   | OK with SmolVLM-500M | Self-contained; no host PC.               |
| Pi-as-thin-client to host PC  | < 1 s/frame   | n/a                | `LlamaServerVLMEngine` POSTs to host.        |

ADR must decide which is v0. Default suggestion: **on-Pi SmolVLM-500M** for v0 (no host-PC dependency); switch to thin-client if latency is unacceptable.

### Draft ADR — to copy into `i3mega-pipettebot/docs/adr/NNNN-overhead-cam-vlm.md`

```markdown
# ADR NNNN — Overhead-cam VLM via qte77/vlm-toolkit

**Status:** Proposed
**Date:** YYYY-MM-DD

## Context

i3 Mega + dPette pipettebot has no closed-loop feedback. Failure modes
(missed wells, no tip, droplet on shaft, foam, spills) are only caught
after the fact by a human watching the bed. We want an overhead USB
camera + automatic anomaly detection that can either log or abort.

Two adjacent qte77 projects need the same primitives (so101-biolab-
automation also wants robot-arm perception). The generic stack —
GGUF VLM engine + YOLO26 detector + pipeline glue — is being
extracted into a shared library at https://github.com/qte77/vlm-toolkit
so both consumers can share one well-tested codebase.

## Decision

1. New module `src/pipettebot/vision/` consumes
   [`vlm-toolkit`](https://github.com/qte77/vlm-toolkit) as a pinned git
   dep behind a new `[vision]` extras group. Stock builds without
   `uv sync --extra vision` are unaffected.
2. Two-stage pipeline: YOLO26n (Ultralytics) for fast trip detection;
   `vlm_toolkit.LlamaCppVLMEngine` with SmolVLM-500M for on-Pi description
   on trip.
3. Failure-mode taxonomy lives in
   `src/pipettebot/vision/failure_modes.py` (project-specific).
4. Camera baseline: any UVC-compliant USB webcam; Logitech C920 as the
   reference. Industrial camera selection deferred.
5. Anomaly response policy v0: **log-and-continue**. Abort-on-detect
   and HITL alert are follow-up ADRs.

## Consequences

- New optional dep on `vlm-toolkit`, `opencv-python`, `ultralytics`,
  `llama-cpp-python`. None pulled in default `uv sync`.
- Pi 5 (8 GB) becomes the supported runtime for vision; Pi 4 / 4 GB Pi 5
  not supported for on-Pi VLM. Documented in README.
- Adds a `make setup_vision` target to download GGUF + YOLO weights.
- `make validate` stays green without vision deps because tests use
  mocked Protocols.

## Alternatives considered

- **Claude Vision API only.** Rejected: ~1,600 tokens/call vs ~120 for
  local VLM; bad fit for long autonomous runs.
- **Embed the VLM code directly in pipettebot.** Rejected: duplicates
  the so101 use case.
- **SAHI for tiny-object detection.** Rejected for v0: overhead-of-deck
  shots have large in-frame wells/tips; YAGNI.
```

---

## B. so101-biolab-automation

**Use case:** Robot-arm perception. Either workspace monitoring (is the
tip rack where the controller thinks it is?) or live anomaly description
during teleoperation. Specific scope is **not yet decided** — so101's
camera path is alive (`opencv-python>=4.10` is a core dep,
`@pytest.mark.hardware` already covers cameras) but no perception module
exists.

**Likely module:** `src/so101/perception/` (alongside the existing
`src/so101/cli/` siblings; mirrors so101 layout conventions).

**`pyproject.toml` change (consumer side):**

```toml
[project.optional-dependencies]
perception = [
    "vlm-toolkit[llamaserver,detector] @ git+https://github.com/qte77/vlm-toolkit.git@<sha>",
]
```

Note `[llamaserver]` not `[llamacpp]` — so101's deployment story is "host
PC drives the robot," so the VLM runs as a `llama-server` daemon on the
same host. That matches so101's existing FastAPI + WebSocket
architecture better than an in-process model load.

**Python target alignment:** so101 is `>=3.12,<3.13`; vlm-toolkit is
`>=3.11,<3.13`. Compatible (so101 is the tighter constraint).

**Decision deferred:**

- Whether perception gates motion (`SafetyMonitor` integration, see
  `.claude/rules/robotics-safety.md`) or is observe-only in v0.
- Camera mounting and calibration belong in a separate so101 ADR.

### Draft ADR stub — to expand and copy into `so101-biolab-automation/docs/adr/NNNN-perception-via-vlm-toolkit.md`

```markdown
# ADR NNNN — Perception via qte77/vlm-toolkit

**Status:** Draft / scope-pending
**Date:** YYYY-MM-DD

## Context

so101-biolab-automation needs camera-driven perception for
[ specific use case TBD: workspace verification? teleoperation
anomaly description? ACT-policy supervisor? ]. The qte77 family has
extracted a shared YOLO + GGUF VLM stack at
https://github.com/qte77/vlm-toolkit so so101 and i3mega-pipettebot
can share the same engine.

## Decision

1. New module `src/so101/perception/` depends on
   [`vlm-toolkit`](https://github.com/qte77/vlm-toolkit) via a new
   `[perception]` extras group.
2. Use the `llamaserver` engine — host PC runs `llama-server`,
   so101 POSTs frames over loopback. Aligns with so101's existing
   FastAPI architecture.
3. Detector model: YOLO26n initially; revisit if accuracy on lab-bench
   classes is insufficient.

## Consequences

- New optional deps: `vlm-toolkit`, `ultralytics`, `httpx`.
- Perception cannot bypass `SafetyMonitor`. Any motion-gating decisions
  flow through the existing `DualArmController` abstraction.
- Tests use mocked `vlm_toolkit.Detector` / `vlm_toolkit.VLMEngine`
  Protocols; live-camera tests get `@pytest.mark.hardware`.

## Open

- Use case to lock before merging this ADR.
- Whether perception output participates in `WANDB` logging for ACT
  training (likely yes, behind `WANDB=1`).
```

---

## C. Adding future consumers

If a third consumer appears later (e.g., a CV-only research project, or
cc-senses-plugin reverses its out-of-scope decision):

1. Open a PR against `vlm-toolkit` adding the consumer to
   `README.md`'s consumers list and a section to this file.
2. The consumer adds its own ADR.
3. No API change should be required — if one is, that's a signal to
   widen the API in `vlm-toolkit` first, ship a minor-version bump, then
   adopt downstream.
