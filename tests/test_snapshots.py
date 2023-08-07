"""Tests for the snapshots module."""
import re
from collections.abc import Hashable, Iterable
from pathlib import Path
from typing import Union

import pytest

from pytest_litter import snapshots


@pytest.fixture(name="tmp_tree_root")
def fixture_tmp_tree_root(tmp_path: Path) -> Path:
    root = tmp_path
    subdir_a = root / "a"
    subdir_a_1 = subdir_a / "a_1"
    subdir_b = root / "b"
    subdir_a_1.mkdir(parents=True, exist_ok=True)
    subdir_b.mkdir()
    a_file = subdir_a / "a_file"
    a_file.touch()
    b_file = subdir_b / "b_file"
    b_file.touch()
    a_1_file = subdir_a_1 / "a_1_file"
    a_1_file.touch()
    return root


@pytest.fixture(name="tree_paths")
def fixture_tree_paths(tmp_tree_root: Path) -> list[snapshots.PathSnapshot]:
    return [
        snapshots.PathSnapshot(path=tmp_tree_root / "a"),
        snapshots.PathSnapshot(path=tmp_tree_root / "a" / "a_file"),
        snapshots.PathSnapshot(path=tmp_tree_root / "b"),
        snapshots.PathSnapshot(path=tmp_tree_root / "b" / "b_file"),
        snapshots.PathSnapshot(path=tmp_tree_root / "a" / "a_1"),
        snapshots.PathSnapshot(path=tmp_tree_root / "a" / "a_1" / "a_1_file"),
    ]


def test_path_snapshot(tmp_tree_root: Path) -> None:
    input_path = tmp_tree_root / "a"
    snapshot = snapshots.PathSnapshot(path=input_path)
    assert str(snapshot) == str(input_path)
    assert str(input_path) in repr(snapshot)
    assert isinstance(snapshot, Hashable)
    assert hash(snapshot) == hash(str(input_path))
    assert snapshot != input_path
    assert snapshot.path == input_path


def test_tree_snapshot__bad_root(tmp_path: Path) -> None:
    input_path = tmp_path / "fake_file"
    with pytest.raises(snapshots.UnexpectedLitterError):
        _ = snapshots.TreeSnapshot(root=input_path)


def test_tree_snapshot(
    tmp_tree_root: Path, tree_paths: list[snapshots.PathSnapshot]
) -> None:
    snapshot = snapshots.TreeSnapshot(root=tmp_tree_root)
    assert snapshot.root == tmp_tree_root
    assert snapshot.paths == frozenset(tree_paths)


@pytest.mark.parametrize(
    "only_a, only_b, expected_match",
    [
        ([], [], True),
        ((), (), True),
        (set(), set(), True),
        ([], [snapshots.PathSnapshot(path=Path("a"))], False),
        ([snapshots.PathSnapshot(path=Path("a"))], [], False),
        (
            [
                snapshots.PathSnapshot(path=Path("a")),
                snapshots.PathSnapshot(path=Path("b")),
            ],
            [],
            False,
        ),
    ],
)
def test_snapshot_comparison(
    only_a: Iterable[snapshots.PathSnapshot],
    only_b: Iterable[snapshots.PathSnapshot],
    expected_match: bool,
) -> None:
    comparison = snapshots.SnapshotComparison(only_a=only_a, only_b=only_b)
    assert comparison.only_a == frozenset(only_a)
    assert comparison.only_b == frozenset(only_b)
    assert comparison.matches == expected_match


@pytest.mark.parametrize(
    "directory, path, expected_match",
    [
        (Path("subdir/a"), snapshots.PathSnapshot(path=Path("subdir/a")), True),
        (Path("subdir/a"), snapshots.PathSnapshot(path=Path("subdir/b")), False),
        (Path("subdir"), snapshots.PathSnapshot(path=Path("subdir/a")), True),
        (Path("subdir"), snapshots.PathSnapshot(path=Path("subdir/subsub/b")), True),
    ],
)
def test_directory_ignore_spec(
    directory: Path, path: snapshots.PathSnapshot, expected_match: bool
) -> None:
    ignore_spec = snapshots.DirectoryIgnoreSpec(directory=directory)
    assert ignore_spec.matches(path=path.path) == expected_match


@pytest.mark.parametrize(
    "regex, path, expected_match",
    [
        (r"sub\w+/a", snapshots.PathSnapshot(path=Path("subdir/a")), True),
        (r"sub\w+/a", snapshots.PathSnapshot(path=Path("subdir/b")), False),
        (re.compile(r"sub\w+/a"), snapshots.PathSnapshot(path=Path("subdir/a")), True),
        (re.compile(r"sub\w+/a"), snapshots.PathSnapshot(path=Path("subdir/b")), False),
    ],
)
def test_regex_ignore_spec(
    regex: Union[str, re.Pattern[str]],
    path: snapshots.PathSnapshot,
    expected_match: bool,
) -> None:
    ignore_spec = snapshots.RegexIgnoreSpec(regex=regex)
    assert ignore_spec.matches(path=path.path) == expected_match


def test_snapshot_comparator__same(tmp_tree_root: Path) -> None:
    snapshot = snapshots.TreeSnapshot(root=tmp_tree_root)
    comparison = snapshots.SnapshotComparator().compare(snapshot, snapshot)
    assert comparison.matches
    assert not comparison.only_a
    assert not comparison.only_b


def test_snapshot_comparator__only_b(tmp_tree_root: Path) -> None:
    snapshot_a = snapshots.TreeSnapshot(root=tmp_tree_root)
    new_file = tmp_tree_root / "new_file"
    new_file.touch()
    snapshot_b = snapshots.TreeSnapshot(root=tmp_tree_root)
    comparison = snapshots.SnapshotComparator().compare(snapshot_a, snapshot_b)
    assert not comparison.matches
    assert not comparison.only_a
    assert comparison.only_b == frozenset((snapshots.PathSnapshot(path=new_file),))


def test_snapshot_comparator__only_a(tmp_tree_root: Path) -> None:
    snapshot_b = snapshots.TreeSnapshot(root=tmp_tree_root)
    new_file = tmp_tree_root / "new_file"
    new_file.touch()
    snapshot_a = snapshots.TreeSnapshot(root=tmp_tree_root)
    comparison = snapshots.SnapshotComparator().compare(snapshot_a, snapshot_b)
    assert not comparison.matches
    assert comparison.only_a == frozenset((snapshots.PathSnapshot(path=new_file),))
    assert not comparison.only_b


@pytest.mark.parametrize(
    "ignore_spec",
    [
        snapshots.RegexIgnoreSpec(regex=r".*/new_file\.\w+"),
    ],
)
def test_snapshot_comparator__only_b__ignored(
    tmp_tree_root: Path, ignore_spec: snapshots.IgnoreSpec
) -> None:
    snapshot_a = snapshots.TreeSnapshot(root=tmp_tree_root)
    (tmp_tree_root / "new_file.txt").touch()
    (tmp_tree_root / "new_file.yml").touch()
    snapshot_b = snapshots.TreeSnapshot(root=tmp_tree_root)
    comparison = snapshots.SnapshotComparator(ignore_specs=[ignore_spec]).compare(
        snapshot_a, snapshot_b
    )
    assert comparison.matches
    assert not comparison.only_a
    assert not comparison.only_b


def test_snapshot_comparator__incompatible_snapshots(tmp_tree_root: Path) -> None:
    snapshot_a = snapshots.TreeSnapshot(root=tmp_tree_root)
    snapshot_b = snapshots.TreeSnapshot(root=tmp_tree_root / "a")
    comparator = snapshots.SnapshotComparator()
    with pytest.raises(snapshots.UnexpectedLitterError):
        _ = comparator.compare(snapshot_a, snapshot_b)
