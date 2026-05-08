import json
import subprocess
from pathlib import Path

import pytest

import stackops.scripts.python.helpers.helpers_seek.seek_impl as seek_impl


def _fake_install_if_missing(*, which: str, binary_name: str | None, verbose: bool) -> None:
    _ = which, binary_name, verbose


def test_run_semantic_search_stops_at_configured_limit(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    for index in range(3):
        tmp_path.joinpath(f"file_{index}.py").write_text("""print("hello")\n""", encoding="utf-8")

    monkeypatch.setattr("stackops.utils.installer_utils.installer_cli.install_if_missing", _fake_install_if_missing)

    seek_impl._run_semantic_search(path=str(tmp_path), query="hello", extension=".py", max_files=2)

    captured = capsys.readouterr()
    assert "--max-files limit of 2" in captured.out


def test_run_semantic_search_allows_disabling_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for index in range(3):
        tmp_path.joinpath(f"file_{index}.py").write_text("""print("hello")\n""", encoding="utf-8")

    captured_options: list[dict[str, str]] = []

    def fake_run(
        args: str | list[str],
        *,
        shell: bool = False,
        check: bool = False,
        stdout: int | None = None,
    ) -> subprocess.CompletedProcess[bytes]:
        _ = stdout
        assert shell is True
        assert check is True
        assert isinstance(args, str)
        results_path = Path(args.split("> ", maxsplit=1)[1].strip())
        payload = {
            "results": [
                {
                    "filename": str(tmp_path.joinpath("file_0.py")),
                    "start_line_number": 1,
                    "end_line_number": 1,
                    "match_line_number": 1,
                    "distance": 0.1,
                    "content": """print("hello")""",
                }
            ]
        }
        results_path.write_text(json.dumps(payload), encoding="utf-8")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=b"")

    def fake_choose_from_dict_with_preview(
        *,
        options_to_preview_mapping: dict[str, str],
        extension: str,
        multi: bool,
        preview_size_percent: float,
    ) -> None:
        assert extension == ".py"
        assert multi is False
        assert preview_size_percent == 75.0
        captured_options.append(options_to_preview_mapping)

    monkeypatch.setattr("stackops.utils.installer_utils.installer_cli.install_if_missing", _fake_install_if_missing)
    monkeypatch.setattr("subprocess.run", fake_run)
    monkeypatch.setattr("stackops.utils.options_utils.tv_options.choose_from_dict_with_preview", fake_choose_from_dict_with_preview)

    seek_impl._run_semantic_search(path=str(tmp_path), query="hello", extension=".py", max_files=0)

    assert len(captured_options) == 1
    assert """print("hello")""" in captured_options[0]
