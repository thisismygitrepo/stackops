

import pytest

from stackops.utils.files import f as file_modes


def test_literal_and_enum_modes_stay_in_sync() -> None:
    literal_modes = set(file_modes.all_t1)
    enum_modes = {member.value for member in file_modes.T1Enum}

    assert literal_modes == enum_modes
    assert file_modes.all_t1_enum == [member.value for member in file_modes.T1Enum]


def test_func_returns_requested_mode(capsys: pytest.CaptureFixture[str]) -> None:
    result = file_modes.func("wb")
    captured = capsys.readouterr()

    assert result == "wb"
    assert "wb" in captured.out
