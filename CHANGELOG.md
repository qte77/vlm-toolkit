# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Python scaffold: `pyproject.toml`, Apache-2.0 `LICENSE`, `NOTICE`, `.gitignore`, `ci` workflow.
- `CODEOWNERS` and this `CHANGELOG.md`.
- Hypothesis property tests for `resize_for_vlm` and `save_jpeg`.

### Fixed

- `resize_for_vlm` no longer fails on extreme aspect ratios (short side clamped to 1 px).
