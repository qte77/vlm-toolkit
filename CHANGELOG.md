# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- README lists `agentic-cax-gauge` as a planned consumer and links `cc-senses-plugin` as related; README and `docs/consumers.md` mark `i3mega-pipettebot` and `so101-biolab-automation` as archived.
- Python scaffold: `pyproject.toml`, Apache-2.0 `LICENSE`, `NOTICE`, `.gitignore`, `ci` workflow.
- `CODEOWNERS` and this `CHANGELOG.md`.
- Hypothesis property tests for `resize_for_vlm` and `save_jpeg`.
- `.github/dependabot.yml`: weekly `github-actions` updates, grouped into
  `actions-security-updates` and `actions-version-updates` (minor/patch;
  majors land as individual PRs).

### Fixed

- `NOTICE` points to `cc-senses-plugin` by its current URL (was the old `cc-voice-plugin-prototype` name).
- `resize_for_vlm` no longer fails on extreme aspect ratios (short side clamped to 1 px).
