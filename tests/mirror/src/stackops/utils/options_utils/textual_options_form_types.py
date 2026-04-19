

from collections.abc import Callable
import json
from pathlib import Path

import pytest

import stackops.utils.accessories as accessories
import stackops.utils.code as code
import stackops.utils.options_utils.textual_options_form as textual_options_form
import stackops.utils.options_utils.textual_options_form_types as form_types
from stackops.utils.options_utils.textual_options_form_types import (
    SelectedOptionMap,
    TextualOptionMap,
)


def test_resolve_uv_run_config_prefers_repo_with_pyproject(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path.joinpath("repo")
    repo_root.mkdir()
    repo_root.joinpath("pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    cwd = repo_root.joinpath("pkg")
    cwd.mkdir()
    module_file = tmp_path.joinpath("outside", "module.py")
    module_file.parent.mkdir()
    module_file.write_text("", encoding="utf-8")

    def fake_get_repo_root(probe_path: Path) -> Path | None:
        return repo_root if probe_path == cwd else None

    monkeypatch.setattr(accessories, "get_repo_root", fake_get_repo_root)

    uv_with, uv_project_dir = form_types.resolve_uv_run_config(cwd=cwd, module_file=module_file)

    assert uv_with == ["textual"]
    assert uv_project_dir == repo_root.as_posix()


def test_resolve_uv_run_config_uses_fallback_when_repo_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get_repo_root(_probe_path: Path) -> Path | None:
        return None

    monkeypatch.setattr(accessories, "get_repo_root", fake_get_repo_root)

    uv_with, uv_project_dir = form_types.resolve_uv_run_config(
        cwd=tmp_path,
        module_file=tmp_path.joinpath("module.py"),
    )

    assert uv_with == ["textual", "stackops>=8.95"]
    assert uv_project_dir is None


def test_use_textual_options_form_runs_lambda_and_reads_json_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_home = tmp_path.joinpath("home")
    fake_home.mkdir()

    def fake_home_method(_cls: type[Path]) -> Path:
        return fake_home

    def fake_randstr(*_args: object, **_kwargs: object) -> str:
        return "token01"

    def fake_resolve_uv_run_config(*, cwd: Path, module_file: Path) -> tuple[list[str], str | None]:
        _ = cwd, module_file
        return ["textual"], tmp_path.as_posix()

    options: TextualOptionMap = {
        "mode": {
            "kind": "select",
            "default": "fast",
            "options": ["fast", "slow"],
        },
        "name": {
            "kind": "text",
            "default": "demo",
            "allow_blank": False,
            "placeholder": "",
        },
    }
    expected: SelectedOptionMap = {"mode": "fast", "name": "demo"}
    captured: list[tuple[list[str], str | None]] = []

    def fake_select_option_values_with_textual(
        option_specs: TextualOptionMap,
        *,
        field_label_width_percent: int,
    ) -> SelectedOptionMap:
        assert option_specs == options
        assert field_label_width_percent == 33
        return expected

    def fake_run_lambda_function(
        func: Callable[[], None],
        *,
        uv_with: list[str],
        uv_project_dir: str | None,
    ) -> None:
        captured.append((uv_with, uv_project_dir))
        func()

    monkeypatch.setattr(form_types.Path, "home", classmethod(fake_home_method))
    monkeypatch.setattr(accessories, "randstr", fake_randstr)
    monkeypatch.setattr(form_types, "resolve_uv_run_config", fake_resolve_uv_run_config)
    monkeypatch.setattr(textual_options_form, "select_option_values_with_textual", fake_select_option_values_with_textual)
    monkeypatch.setattr(code, "run_lambda_function", fake_run_lambda_function)

    result = form_types.use_textual_options_form(options, field_label_width_percent=33)

    result_path = fake_home.joinpath("tmp_results", "textual_options_form", "token01.json")
    assert result == expected
    assert json.loads(result_path.read_text(encoding="utf-8")) == expected
    assert captured == [(["textual"], tmp_path.as_posix())]
