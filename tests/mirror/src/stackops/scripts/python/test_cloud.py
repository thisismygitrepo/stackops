from unittest.mock import Mock

import pytest
from typer.testing import CliRunner

from stackops.scripts.python.cloud import get_app
from stackops.scripts.python.helpers.helpers_cloud import cloud_copy


@pytest.mark.parametrize(
    ("arguments", "enabled"),
    [
        ([], None),
        (["--overwrite"], "overwrite"),
        (["-o"], "overwrite"),
        (["--rel2home"], "rel2home"),
        (["-r"], "rel2home"),
        (["--zip"], "zip_"),
        (["-z"], "zip_"),
        (["--os-specific"], "os_specific"),
        (["-O"], "os_specific"),
    ],
)
def test_copy_flags_enable_only_the_requested_feature(
    monkeypatch: pytest.MonkeyPatch, arguments: list[str], enabled: str | None
) -> None:
    copy_main = Mock()
    monkeypatch.setattr(cloud_copy, "main", copy_main)

    result = CliRunner().invoke(get_app(), ["copy", "source", "target", *arguments])

    assert result.exit_code == 0, result.output
    copy_main.assert_called_once()
    for parameter in ("overwrite", "rel2home", "zip_", "os_specific"):
        assert copy_main.call_args.kwargs[parameter] is (parameter == enabled)


@pytest.mark.parametrize("flag", ["--no-overwrite", "--no-rel2home", "--no-zip", "--no-os-specific"])
def test_copy_rejects_flags_that_repeat_the_default(flag: str) -> None:
    result = CliRunner().invoke(get_app(), ["copy", "source", "target", flag])
    assert result.exit_code == 2
    assert "No such option" in result.output
