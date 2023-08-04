"""Pytest plugin code."""

from typing import Optional

import pytest

from pytest_litter.plugin.utils import (
    COMPARATOR_KEY,
    SNAPSHOT_KEY,
    raise_test_error_from_comparison,
    run_snapshot_comparison,
)
from pytest_litter.snapshots import (
    DirectoryIgnoreSpec,
    IgnoreSpec,
    RegexIgnoreSpec,
    SnapshotComparator,
    TreeSnapshot,
)


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest-litter plugin (pytest hook function)."""
    ignore_specs: list[IgnoreSpec] = []
    basetemp: Optional[str] = config.getoption("basetemp", None)
    if basetemp is not None:
        ignore_specs.append(
            DirectoryIgnoreSpec(
                directory=config.rootpath / basetemp,
            )
        )
    ignore_specs.append(RegexIgnoreSpec(regex=r".*/__pycache__.*"))
    config.stash[SNAPSHOT_KEY] = TreeSnapshot(root=config.rootpath)
    config.stash[COMPARATOR_KEY] = SnapshotComparator(ignore_specs=ignore_specs)


@pytest.hookimpl(hookwrapper=True)  # type: ignore[misc]
def pytest_runtest_call(item: pytest.Item):  # type: ignore[no-untyped-def]
    yield
    run_snapshot_comparison(
        test_name=item.name,
        config=item.config,
        mismatch_cb=raise_test_error_from_comparison,
    )
