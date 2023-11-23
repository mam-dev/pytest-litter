"""Pytest plugin code."""

from typing import Optional

import pytest

from pytest_litter.plugin.utils import (
    COMPARATOR_KEY,
    SNAPSHOT_FACTORY_KEY,
    SNAPSHOT_KEY,
    raise_test_error_from_comparison,
    run_snapshot_comparison,
)
from pytest_litter.snapshots import (
    DirectoryIgnoreSpec,
    IgnoreSpec,
    LitterConfig,
    NameIgnoreSpec,
    SnapshotComparator,
    TreeSnapshotFactory,
)

PARSER_GROUP = "pytest-litter"
RUN_CHECK_OPTION_DEST_NAME = "check_litter"


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add options to pytest (pytest hook function)."""
    group = parser.getgroup(PARSER_GROUP)
    group.addoption(
        "--check-litter",
        action="store_true",
        dest=RUN_CHECK_OPTION_DEST_NAME,
        help="Fail if tests create/remove files.",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest-litter plugin (pytest hook function)."""
    if not config.getoption(RUN_CHECK_OPTION_DEST_NAME):
        return
    ignore_specs: list[IgnoreSpec] = []
    basetemp: Optional[str] = config.getoption("basetemp", None)
    if basetemp is not None:
        ignore_specs.append(
            DirectoryIgnoreSpec(
                directory=config.rootpath / basetemp,
            )
        )
    ignore_specs.append(NameIgnoreSpec(name="__pycache__"))
    ignore_specs.append(NameIgnoreSpec(name="venv"))
    ignore_specs.append(NameIgnoreSpec(name=".venv"))
    ignore_specs.append(NameIgnoreSpec(name=".pytest_cache"))
    litter_config = LitterConfig(ignore_specs=ignore_specs)
    snapshot_factory = TreeSnapshotFactory(config=litter_config)
    config.stash[SNAPSHOT_FACTORY_KEY] = snapshot_factory
    config.stash[SNAPSHOT_KEY] = snapshot_factory.create_snapshot(root=config.rootpath)
    config.stash[COMPARATOR_KEY] = SnapshotComparator(config=litter_config)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item: pytest.Item):  # type: ignore[no-untyped-def]
    yield
    if item.config.getoption(RUN_CHECK_OPTION_DEST_NAME):
        run_snapshot_comparison(
            test_name=item.name,
            config=item.config,
            mismatch_cb=raise_test_error_from_comparison,
        )
