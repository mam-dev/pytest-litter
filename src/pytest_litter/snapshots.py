"""Module related to taking and comparing snapshots of directory trees."""
import abc
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Optional, Union


class UnexpectedLitterError(Exception):
    """Error that should not occur normally, indicative of some programming error."""


class IgnoreSpec(abc.ABC):
    """Specification about paths to ignore in comparisons."""

    __slots__ = ()

    @abc.abstractmethod
    def matches(self, path: Path) -> bool:
        ...  # pragma: no cover


class DirectoryIgnoreSpec(IgnoreSpec):
    """Specification to ignore everything in a given directory."""

    __slots__ = ("_directory",)

    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def matches(self, path: Path) -> bool:
        return self._directory == path or self._directory in path.parents


class NameIgnoreSpec(IgnoreSpec):
    """Specification to ignore all directories/files with a given name."""

    __slots__ = ("_name",)

    def __init__(self, name: str) -> None:
        self._name = name

    def matches(self, path: Path) -> bool:
        return self._name in path.parts


class RegexIgnoreSpec(IgnoreSpec):
    """Regex-based specification about paths to ignore in comparisons."""

    __slots__ = ("_regex",)

    def __init__(self, regex: Union[str, re.Pattern[str]]) -> None:
        self._regex: re.Pattern[str] = re.compile(regex)

    def matches(self, path: Path) -> bool:
        return self._regex.fullmatch(str(path)) is not None


class LitterConfig:
    """Configuration for pytest-litter."""

    __slots__ = ("_ignore_specs",)

    def __init__(self, ignore_specs: Optional[Iterable[IgnoreSpec]] = None) -> None:
        """Initialize.

        Args:
            ignore_specs: Specifies paths to ignore when doing the comparison.

        """
        self._ignore_specs: frozenset[IgnoreSpec] = frozenset(ignore_specs or [])

    @property
    def ignore_specs(self) -> frozenset[IgnoreSpec]:
        return self._ignore_specs


class PathSnapshot:
    """A snapshot of a path."""

    __slots__ = ("_path",)

    def __init__(self, path: Path) -> None:
        self._path: Path = path

    def __str__(self) -> str:
        return str(self._path)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._path})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, PathSnapshot):
            return False
        return str(self) == str(other)

    def __hash__(self) -> int:
        return hash(str(self._path))

    @property
    def path(self) -> Path:
        return self._path


class TreeSnapshot:
    """A snapshot of a directory tree."""

    __slots__ = ("_root", "_paths")

    def __init__(self, root: Path, paths: Iterable[Path]) -> None:
        """Initialize.

        Args:
            root: The root directory of the tree.
            paths: All paths in the snapshot.

        """
        if not root.is_dir():
            raise UnexpectedLitterError(f"'{root}' is not a directory.")
        self._root: Path = root
        self._paths: frozenset[PathSnapshot] = frozenset(
            PathSnapshot(path=path) for path in paths
        )

    @property
    def root(self) -> Path:
        """The root directory of the tree."""
        return self._root

    @property
    def paths(self) -> frozenset[PathSnapshot]:
        """The paths in the snapshot."""
        return self._paths


class TreeSnapshotFactory:
    """Factory class for TreeSnapshotFactory."""

    __slots__ = ("_ignore_specs",)

    def __init__(self, config: LitterConfig) -> None:
        """Initialize.

        Args:
            config: pytest-litter configuration.

        """
        self._ignore_specs: frozenset[IgnoreSpec] = frozenset(config.ignore_specs or [])

    def _should_be_ignored(self, path: Path) -> bool:
        return path.name == "." or any(
            ignore_spec.matches(path) for ignore_spec in self._ignore_specs
        )

    def create_snapshot(self, root: Path) -> TreeSnapshot:
        paths: set[Path] = set()

        def traverse(current: Path) -> None:
            sub_paths = {
                p for p in current.glob("*") if not self._should_be_ignored(path=p)
            }
            paths.update(sub_paths)
            for sub_path in sub_paths:
                traverse(sub_path)

        traverse(root)

        return TreeSnapshot(
            root=root,
            paths=paths,
        )


class SnapshotComparison:
    """A comparison of two TreeSnapshots."""

    __slots__ = ("_only_a", "_only_b")

    def __init__(
        self, only_a: Iterable[PathSnapshot], only_b: Iterable[PathSnapshot]
    ) -> None:
        """Initialize.

        Args:
            only_a: Paths found only in snapshot A.
            only_b: Paths found only in snapshot B.

        """
        self._only_a: frozenset[PathSnapshot] = frozenset(only_a)
        self._only_b: frozenset[PathSnapshot] = frozenset(only_b)

    @property
    def only_a(self) -> frozenset[PathSnapshot]:
        """Paths found only in snapshot A."""
        return self._only_a

    @property
    def only_b(self) -> frozenset[PathSnapshot]:
        """Paths found only in snapshot B."""
        return self._only_b

    @property
    def matches(self) -> bool:
        """If snapshots A and B match each other."""
        return not self._only_a and not self._only_b


class SnapshotComparator:
    """Compare TreeSnapshots with each other."""

    __slots__ = ("_ignore_specs",)

    def __init__(self, config: LitterConfig) -> None:
        """Initialize.

        Args:
            config: pytest-litter configuration.

        """
        self._ignore_specs: frozenset[IgnoreSpec] = frozenset(config.ignore_specs or [])

    @staticmethod
    def compare(
        snapshot_a: TreeSnapshot, snapshot_b: TreeSnapshot
    ) -> SnapshotComparison:
        """Compare snapshot_a and snapshot_b to produce a SnapshotComparison."""
        if snapshot_a.root != snapshot_b.root:
            raise UnexpectedLitterError(
                f"Comparing a snapshot of {snapshot_a.root} vs one of {snapshot_b.root}"
            )
        common_paths: frozenset[PathSnapshot] = snapshot_a.paths.intersection(
            snapshot_b.paths
        )
        return SnapshotComparison(
            only_a=snapshot_a.paths - common_paths,
            only_b=snapshot_b.paths - common_paths,
        )
