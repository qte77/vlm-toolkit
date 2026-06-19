# vlm-toolkit

Local GGUF VLM + small-object detector for headless robotics and CLI use.

- Two-stage pipeline: YOLO26 fast detector → GGUF VLM describer.
- Backends: in-process (`llama-cpp-python`) or HTTP (`llama-server`).
- Python `>=3.11,<3.13`. Apache-2.0.

**Status:** Draft / pre-`v0.1.0`. Public API is not yet stable.

**Background:** used as the *perceive* step of a [self-driving-lab agent loop](https://qte77.github.io/open-self-driving-lab-agent-loop/).

**Consumers (planned):**

- [qte77/i3mega-pipettebot](https://github.com/qte77/i3mega-pipettebot) — overhead-cam pipetting anomaly detection.
- [qte77/so101-biolab-automation](https://github.com/qte77/so101-biolab-automation) — dual SO-101 robot-arm perception.

- [`docs/architecture.md`](docs/architecture.md) — scope, locked decisions, public API, branch protection.
- [`docs/UserStory.md`](docs/UserStory.md) — acceptance criteria for `v0.1.0`.
- [`docs/consumers.md`](docs/consumers.md) — integration drafts and ADR text for downstream repos.
