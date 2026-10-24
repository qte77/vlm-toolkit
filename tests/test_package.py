from importlib.metadata import version

import vlm_toolkit


def test_version_matches_distribution_metadata() -> None:
    assert vlm_toolkit.__version__ == version("vlm-toolkit")
