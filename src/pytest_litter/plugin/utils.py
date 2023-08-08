from collections.abc import Iterable
from pathlib import Path
from typing import Callable

import pytest

from pytest_litter.snapshots import (
    SnapshotComparator,
    SnapshotComparison,
    TreeSnapshot,
    TreeSnapshotFactory,
)

SNAPSHOT_FACTORY_KEY = pytest.StashKey[TreeSnapshotFactory]()
SNAPSHOT_KEY = pytest.StashKey[TreeSnapshot]()
COMPARATOR_KEY = pytest.StashKey[SnapshotComparator]()


class ProblematicTestLitterError(Exception):
    """Raised when a test causes littering, i.e., modifies file tree."""


def format_test_snapshot_mismatch_message(
    test_name: str, paths_added: Iterable[Path], paths_deleted: Iterable[Path]
) -> str:
    def _iterable_to_human_readable(iterable: Iterable[Path]) -> str:
        return ", ".join(f"'{x}'" for x in iterable)

    message = f"The test '{test_name}'"
    if paths_added:
        message += f" added {_iterable_to_human_readable(paths_added)}"
        if paths_deleted:
            message += " and"
    if paths_deleted:
        message += f" deleted {_iterable_to_human_readable(paths_deleted)}"
    return message


def raise_test_error_from_comparison(
    test_name: str, comparison: SnapshotComparison
) -> None:
    """Raise ProblematicTestLitterError for test_name based on comparison."""
    raise ProblematicTestLitterError(
        format_test_snapshot_mismatch_message(
            test_name=test_name,
            paths_added=tuple(p.path for p in comparison.only_b),
            paths_deleted=tuple(p.path for p in comparison.only_a),
        )
    )


def run_snapshot_comparison(
    test_name: str,
    config: pytest.Config,
    mismatch_cb: Callable[[str, SnapshotComparison], None],
) -> None:
    """Compare current and old snapshots and call mismatch_cb if there is a mismatch."""
    original_snapshot: TreeSnapshot = config.stash[SNAPSHOT_KEY]
    snapshot_factory: TreeSnapshotFactory = config.stash[SNAPSHOT_FACTORY_KEY]
    new_snapshot: TreeSnapshot = snapshot_factory.create_snapshot(
        root=original_snapshot.root
    )
    config.stash[SNAPSHOT_KEY] = new_snapshot

    comparator: SnapshotComparator = config.stash[COMPARATOR_KEY]
    comparison: SnapshotComparison = comparator.compare(original_snapshot, new_snapshot)

    if not comparison.matches:
        mismatch_cb(test_name, comparison)
