from __future__ import annotations

import importlib
import logging
import sys
from collections.abc import Iterator

import pytest


def _reset_machineconfig_root_logger() -> None:
    root = logging.getLogger("machineconfig")
    for handler in tuple(root.handlers):
        root.removeHandler(handler)
        handler.close()
    root.setLevel(logging.NOTSET)
    root.propagate = True


@pytest.fixture(autouse=True)
def _reset_logger_state() -> Iterator[None]:
    _reset_machineconfig_root_logger()
    yield
    _reset_machineconfig_root_logger()


def test_import_configures_root_logger_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MC_LOG_LEVEL", "debug")

    import machineconfig.logger as logger_module

    logger_module = importlib.reload(logger_module)
    root_logger = logger_module.get_logger()

    assert root_logger.name == "machineconfig"
    assert root_logger.level == logging.DEBUG
    assert len(root_logger.handlers) == 1
    assert isinstance(root_logger.handlers[0], logging.StreamHandler)
    assert root_logger.handlers[0].stream is sys.stdout
    assert root_logger.propagate is False


def test_reload_keeps_single_handler_and_returns_child_logger(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MC_LOG_LEVEL", raising=False)

    import machineconfig.logger as logger_module

    first_import = importlib.reload(logger_module)
    second_import = importlib.reload(logger_module)
    root_logger = second_import.get_logger()
    child_logger = second_import.get_logger("jobs.sync")

    assert first_import.get_logger() is root_logger
    assert len(root_logger.handlers) == 1
    assert child_logger.name == "machineconfig.jobs.sync"
    assert child_logger.parent is root_logger
