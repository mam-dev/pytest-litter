"""Tests using pytest-litter intended for testing with pytester."""
from pathlib import Path

import pytest


def tc_should_pass() -> None:
    """Do not create any litter."""


@pytest.mark.xfail
def tc_should_fail() -> None:
    """Create a file 'litter' in cwd which is not cleaned up."""
    (Path.cwd() / "litter").touch()


def tc_should_also_pass(tmp_path: Path) -> None:
    """Create litter in tmp_path only."""
    (tmp_path / "more_litter").touch()


@pytest.mark.xfail
def tc_should_also_fail() -> None:
    """Remove a file 'litter' in cwd."""
    (Path.cwd() / "litter").unlink()
