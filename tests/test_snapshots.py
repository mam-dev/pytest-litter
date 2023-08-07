"""Tests for the snapshots module."""
import re
from collections.abc import Hashable, Iterable
from pathlib import Path
from typing import Optional, Union

import pytest

from pytest_litter import snapshots


@pytest.fixture(name="empty_config")
def fixture_empty_config() -> snapshots.LitterConfig:
    return snapshots.LitterConfig()


@pytest.fixture(name="snapshot_factory")
def fixture_snapshot_factory(
    empty_config: snapshots.LitterConfig,
) -> snapshots.TreeSnapshotFactory:
    return snapshots.TreeSnapshotFactory(config=empty_config)


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
def fixture_tree_paths(tmp_tree_root: Path) -> list[Path]:
    return [
        tmp_tree_root / "a",
        tmp_tree_root / "a" / "a_file",
        tmp_tree_root / "b",
        tmp_tree_root / "b" / "b_file",
        tmp_tree_root / "a" / "a_1",
        tmp_tree_root / "a" / "a_1" / "a_1_file",
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
        # paths are irrelevant here
        _ = snapshots.TreeSnapshot(root=input_path, paths=[])


def test_tree_snapshot(tmp_tree_root: Path, tree_paths: list[Path]) -> None:
    snapshot = snapshots.TreeSnapshot(root=tmp_tree_root, paths=tree_paths)
    assert snapshot.root == tmp_tree_root
    assert snapshot.paths == frozenset(
        snapshots.PathSnapshot(path) for path in tree_paths
    )


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


def test_snapshot_comparator__same(
    empty_config: snapshots.LitterConfig, tmp_tree_root: Path, tree_paths: list[Path]
) -> None:
    snapshot = snapshots.TreeSnapshot(root=tmp_tree_root, paths=tree_paths)
    comparison = snapshots.SnapshotComparator(config=empty_config).compare(
        snapshot, snapshot
    )
    assert comparison.matches
    assert not comparison.only_a
    assert not comparison.only_b


def test_snapshot_comparator__only_b(
    empty_config: snapshots.LitterConfig, tmp_tree_root: Path, tree_paths: list[Path]
) -> None:
    snapshot_a = snapshots.TreeSnapshot(root=tmp_tree_root, paths=tree_paths)
    new_file = tmp_tree_root / "new_file"
    tree_paths.append(new_file)
    snapshot_b = snapshots.TreeSnapshot(root=tmp_tree_root, paths=tree_paths)
    comparison = snapshots.SnapshotComparator(config=empty_config).compare(
        snapshot_a, snapshot_b
    )
    assert not comparison.matches
    assert not comparison.only_a
    assert comparison.only_b == frozenset((snapshots.PathSnapshot(path=new_file),))


def test_snapshot_comparator__only_a(
    empty_config: snapshots.LitterConfig, tmp_tree_root: Path, tree_paths: list[Path]
) -> None:
    snapshot_b = snapshots.TreeSnapshot(root=tmp_tree_root, paths=tree_paths)
    new_file = tmp_tree_root / "new_file"
    tree_paths.append(new_file)
    snapshot_a = snapshots.TreeSnapshot(root=tmp_tree_root, paths=tree_paths)
    comparison = snapshots.SnapshotComparator(config=empty_config).compare(
        snapshot_a, snapshot_b
    )
    assert not comparison.matches
    assert comparison.only_a == frozenset((snapshots.PathSnapshot(path=new_file),))
    assert not comparison.only_b


def test_snapshot_comparator__incompatible_snapshots(
    empty_config: snapshots.LitterConfig, tmp_tree_root: Path
) -> None:
    # TreeSnapshot paths are incorrect, but that is irrelevant for this test.
    snapshot_a = snapshots.TreeSnapshot(root=tmp_tree_root, paths=[])
    snapshot_b = snapshots.TreeSnapshot(root=tmp_tree_root / "a", paths=[])
    comparator = snapshots.SnapshotComparator(config=empty_config)
    with pytest.raises(snapshots.UnexpectedLitterError):
        _ = comparator.compare(snapshot_a, snapshot_b)


@pytest.mark.parametrize(
    "ignore_specs", [None, [], [snapshots.RegexIgnoreSpec(regex=r".*")]]
)
def test_litter_config(ignore_specs: Optional[Iterable[snapshots.IgnoreSpec]]) -> None:
    config = snapshots.LitterConfig(ignore_specs=ignore_specs)
    assert config.ignore_specs == frozenset(ignore_specs or [])


class _FakeIgnoreSpec(snapshots.IgnoreSpec):
    def matches(self, path: Path) -> bool:
        return "a" in path.parts


@pytest.mark.parametrize(
    "config, expected_paths",
    [
        (
            snapshots.LitterConfig(),
            [
                Path("a"),
                Path("a/a_file"),
                Path("a/a_1"),
                Path("a/a_1/a_1_file"),
                Path("b"),
                Path("b/b_file"),
            ],
        ),
        (
            snapshots.LitterConfig(ignore_specs=[_FakeIgnoreSpec()]),
            [Path("b"), Path("b/b_file")],
        ),
    ],
)
def test_create_snapshot(
    config: snapshots.LitterConfig, expected_paths: list[Path], tmp_tree_root: Path
) -> None:
    factory = snapshots.TreeSnapshotFactory(config=config)
    snapshot: snapshots.TreeSnapshot = factory.create_snapshot(root=tmp_tree_root)
    assert {str(p) for p in snapshot.paths} == {
        str(tmp_tree_root / path) for path in expected_paths
    }


@pytest.mark.parametrize(
    "name, path, expected_match",
    [
        ("c", Path("a/b/c"), True),
        ("c", Path("a/b"), False),
        ("a", Path("a/b"), True),
    ],
)
def test_name_ignore_spec(name: str, path: Path, expected_match: bool) -> None:
    assert snapshots.NameIgnoreSpec(name=name).matches(path=path) == expected_match
