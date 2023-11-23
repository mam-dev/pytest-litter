"""Tests for the plugin module."""
import itertools
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Optional
from unittest.mock import ANY, Mock, call

import pytest

from pytest_litter import snapshots
from pytest_litter.plugin import plugin, utils

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch


@pytest.mark.parametrize(
    "test_name, paths_added, paths_deleted, expected_msg",
    [
        ("test_fake", [Path("new")], [], "The test 'test_fake' added 'new'"),
        (
            "test_madeup",
            [Path("new"), Path("newer"), Path("newest")],
            [],
            "The test 'test_madeup' added 'new', 'newer', 'newest'",
        ),
        (
            "test_fake",
            [Path("new")],
            [Path("gone")],
            "The test 'test_fake' added 'new' and deleted 'gone'",
        ),
        (
            "test_fake",
            [Path("new"), Path("newer")],
            [Path("gone"), Path("deleted")],
            "The test 'test_fake' added 'new', 'newer' and deleted 'gone', 'deleted'",
        ),
        (
            "test_fake",
            [],
            [Path("gone")],
            "The test 'test_fake' deleted 'gone'",
        ),
    ],
)
def test_format_test_snapshot_mismatch_message(
    test_name: str,
    paths_added: Iterable[Path],
    paths_deleted: Iterable[Path],
    expected_msg: str,
) -> None:
    actual_msg = utils.format_test_snapshot_mismatch_message(
        test_name=test_name,
        paths_added=paths_added,
        paths_deleted=paths_deleted,
    )
    assert actual_msg == expected_msg


def test_raise_test_error_from_comparison(
    monkeypatch: "MonkeyPatch", tmp_path: Path
) -> None:
    test_name = "test_fake"
    path_a = tmp_path / "a"
    path_b = tmp_path / "b"
    fake_error_msg = "fake message"
    mock_format = Mock(
        spec=utils.format_test_snapshot_mismatch_message,
        return_value=fake_error_msg,
    )
    monkeypatch.setattr(
        "pytest_litter.plugin.utils.format_test_snapshot_mismatch_message",
        mock_format,
    )
    mock_comparison = Mock(
        spec=snapshots.SnapshotComparison,
        test_name=test_name,
        only_a=[Mock(spec=snapshots.PathSnapshot, path=path_a)],
        only_b=[Mock(spec=snapshots.PathSnapshot, path=path_b)],
    )

    with pytest.raises(utils.ProblematicTestLitterError, match=fake_error_msg):
        utils.raise_test_error_from_comparison(
            test_name=test_name,
            comparison=mock_comparison,
        )
    mock_format.assert_called_once_with(
        test_name=test_name,
        paths_added=(path_b,),
        paths_deleted=(path_a,),
    )


@pytest.mark.parametrize("matches", [False, True])
def test_run_snapshot_comparison(
    monkeypatch: "MonkeyPatch",
    tmp_path: Path,
    matches: bool,
) -> None:
    test_name = "test_fake"
    mock_factory = Mock(spec=snapshots.TreeSnapshotFactory)
    mock_snapshot_new = Mock(spec=snapshots.TreeSnapshot)
    mock_factory.create_snapshot.return_value = mock_snapshot_new
    mock_snapshot_old = Mock(spec=snapshots.TreeSnapshot, root=tmp_path)
    mock_comparator = Mock(spec=snapshots.SnapshotComparator)
    mock_comparator.compare.return_value = Mock(
        spec=snapshots.SnapshotComparison, matches=matches
    )
    mock_config = Mock(
        spec=pytest.Config,
        stash={
            utils.SNAPSHOT_KEY: mock_snapshot_old,
            utils.SNAPSHOT_FACTORY_KEY: mock_factory,
            utils.COMPARATOR_KEY: mock_comparator,
        },
    )
    mock_cb = Mock()

    def fake_cb(tc: str, comparison: snapshots.SnapshotComparison) -> None:
        mock_cb(tc, comparison)

    utils.run_snapshot_comparison(
        test_name=test_name,
        config=mock_config,
        mismatch_cb=fake_cb,
    )

    mock_factory.create_snapshot.assert_called_once_with(root=mock_snapshot_old.root)
    mock_comparator.compare.assert_called_once_with(
        mock_snapshot_old,
        mock_snapshot_new,
    )
    assert mock_config.stash[utils.SNAPSHOT_KEY] is mock_snapshot_new
    if matches:
        mock_cb.assert_not_called()
    else:
        mock_cb.assert_called_once_with(test_name, mock_comparator.compare.return_value)


def test_pytest_addoption() -> None:
    mock_parser = Mock(spec=pytest.Parser)
    plugin.pytest_addoption(mock_parser)
    assert mock_parser.mock_calls == [
        call.getgroup("pytest-litter"),
        call.getgroup().addoption(
            "--check-litter",
            action="store_true",
            dest=plugin.RUN_CHECK_OPTION_DEST_NAME,
            help=ANY,
        ),
    ]


@pytest.mark.parametrize(
    "run_check, basetemp", itertools.product([True, False], [None, Path("tmp")])
)
def test_pytest_configure(
    monkeypatch: "MonkeyPatch", run_check: bool, basetemp: Optional[Path]
) -> None:
    mock_snapshot_factory_cls = Mock(spec=snapshots.TreeSnapshotFactory)
    monkeypatch.setattr(
        "pytest_litter.plugin.plugin.TreeSnapshotFactory",
        mock_snapshot_factory_cls,
    )
    mock_comparator_cls = Mock(spec=snapshots.SnapshotComparator)
    monkeypatch.setattr(
        "pytest_litter.plugin.plugin.SnapshotComparator",
        mock_comparator_cls,
    )
    mock_config = Mock(
        spec=pytest.Config,
        rootpath=Path("rootpath"),
        stash={},
        getoption=Mock(spec=pytest.Config.getoption, side_effect=[run_check, basetemp]),
    )
    mock_litter_config_cls = Mock(spec=snapshots.LitterConfig)
    monkeypatch.setattr(
        "pytest_litter.plugin.plugin.LitterConfig", mock_litter_config_cls
    )
    mock_dir_ignore_spec = Mock(spec=snapshots.DirectoryIgnoreSpec)
    monkeypatch.setattr(
        "pytest_litter.plugin.plugin.DirectoryIgnoreSpec",
        mock_dir_ignore_spec,
    )
    mock_name_ignore_spec = Mock(spec=snapshots.NameIgnoreSpec)
    monkeypatch.setattr(
        "pytest_litter.plugin.plugin.NameIgnoreSpec",
        mock_name_ignore_spec,
    )
    expected_ignore_specs = []
    if basetemp is not None:
        expected_ignore_specs.append(mock_dir_ignore_spec.return_value)
    expected_ignore_specs.append(mock_name_ignore_spec.return_value)
    expected_ignore_specs.append(mock_name_ignore_spec.return_value)
    expected_ignore_specs.append(mock_name_ignore_spec.return_value)
    expected_ignore_specs.append(mock_name_ignore_spec.return_value)

    plugin.pytest_configure(mock_config)

    expected_getoption_calls = [
        call(plugin.RUN_CHECK_OPTION_DEST_NAME),
    ]
    if run_check:
        expected_getoption_calls.append(call("basetemp", None))
    assert mock_config.getoption.mock_calls == expected_getoption_calls

    if run_check:
        mock_litter_config_cls.assert_called_once_with(
            ignore_specs=expected_ignore_specs,
        )
        mock_snapshot_factory_cls.assert_called_once_with(
            config=mock_litter_config_cls.return_value
        )
        mock_snapshot_factory_cls.return_value.create_snapshot.assert_called_once_with(
            root=mock_config.rootpath
        )
        assert (
            mock_config.stash[utils.SNAPSHOT_FACTORY_KEY]
            is mock_snapshot_factory_cls.return_value
        )
        assert (
            mock_config.stash[utils.SNAPSHOT_KEY]
            is mock_snapshot_factory_cls.return_value.create_snapshot.return_value
        )
        assert (
            mock_config.stash[utils.COMPARATOR_KEY] is mock_comparator_cls.return_value
        )

        if basetemp is not None:
            mock_dir_ignore_spec.assert_has_calls(
                [call(directory=mock_config.rootpath / basetemp)]
            )
        else:
            mock_dir_ignore_spec.assert_not_called()
        mock_name_ignore_spec.assert_has_calls(
            [
                call(name="__pycache__"),
                call(name="venv"),
                call(name=".venv"),
                call(name=".pytest_cache"),
            ]
        )
    else:
        mock_litter_config_cls.assert_not_called()
        mock_snapshot_factory_cls.assert_not_called()
        assert utils.SNAPSHOT_FACTORY_KEY not in mock_config.stash
        assert utils.SNAPSHOT_KEY not in mock_config.stash
        assert utils.COMPARATOR_KEY not in mock_config.stash


def test_pytest_runtest_call(monkeypatch: "MonkeyPatch") -> None:
    mock_raise_test_error = Mock(spec=utils.raise_test_error_from_comparison)
    monkeypatch.setattr(
        "pytest_litter.plugin.plugin.raise_test_error_from_comparison",
        mock_raise_test_error,
    )
    mock_run_comparison = Mock(spec=utils.run_snapshot_comparison)
    monkeypatch.setattr(
        "pytest_litter.plugin.plugin.run_snapshot_comparison",
        mock_run_comparison,
    )
    mock_item = Mock(spec=pytest.Item)
    mock_item.name = "test_fake"
    mock_item.config = Mock(spec=pytest.Config)

    # The list comprehension is just to get past the yield statement#
    _ = list(plugin.pytest_runtest_call(mock_item))

    mock_run_comparison.assert_called_once_with(
        test_name=mock_item.name,
        config=mock_item.config,
        mismatch_cb=mock_raise_test_error,
    )


def test_pytest_runtest_call__no_check_litter(monkeypatch: "MonkeyPatch") -> None:
    mock_run_comparison = Mock(spec=utils.run_snapshot_comparison)
    monkeypatch.setattr(
        "pytest_litter.plugin.plugin.run_snapshot_comparison",
        mock_run_comparison,
    )
    mock_item = Mock(spec=pytest.Item)
    mock_item.config = Mock(spec=pytest.Config)
    mock_item.config.getoption.return_value = False

    # The list comprehension is just to get past the yield statement#
    _ = list(plugin.pytest_runtest_call(mock_item))

    mock_item.config.getoption.assert_called_once_with(
        plugin.RUN_CHECK_OPTION_DEST_NAME
    )
    mock_run_comparison.assert_not_called()


@pytest.mark.integration_test
def test_plugin_with_pytester__check_litter(pytester: pytest.Pytester) -> None:
    # pytester uses basetemp internally, so the case without basetemp
    # cannot be tested using pytester.
    pytester.copy_example("pytest.ini")
    pytester.copy_example("suite_tests.py")
    result: pytest.RunResult = pytester.runpytest("--check-litter")
    result.assert_outcomes(passed=2, xfailed=2)


@pytest.mark.integration_test
def test_plugin_with_pytester__no_check_litter(pytester: pytest.Pytester) -> None:
    # pytester uses basetemp internally, so the case without basetemp
    # cannot be tested using pytester.
    pytester.copy_example("pytest.ini")
    pytester.copy_example("suite_tests.py")
    result: pytest.RunResult = pytester.runpytest()
    result.assert_outcomes(passed=2, xpassed=2)
