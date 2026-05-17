import json
from pathlib import Path

import pytest

from stackops.scripts.python.ai.scripts import models


def test_build_checker_specs_uses_distinct_pyright_override_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    tmp_path.joinpath("pyproject.toml").write_text(
        """
[project]
name = "demo"
version = "0.1.0"
requires-python = ">=3.13"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    tmp_path.joinpath("pyrightconfig.json").write_text(
        '{"exclude": [".venv"]}\n', encoding="utf-8"
    )

    first_specs = models.build_checker_specs(("tests",))
    second_specs = models.build_checker_specs((".ai",))

    first_pyright_spec = next(spec for spec in first_specs if spec.slug == "pyright")
    second_pyright_spec = next(spec for spec in second_specs if spec.slug == "pyright")
    first_override_path = Path(
        first_pyright_spec.command[first_pyright_spec.command.index("--project") + 1]
    )
    second_override_path = Path(
        second_pyright_spec.command[second_pyright_spec.command.index("--project") + 1]
    )

    assert first_override_path != second_override_path
    assert first_override_path.exists()
    assert second_override_path.exists()
    assert json.loads(first_override_path.read_text(encoding="utf-8")) == {
        "extends": "./pyrightconfig.json",
        "exclude": [".venv", "tests"],
    }
    assert json.loads(second_override_path.read_text(encoding="utf-8")) == {
        "extends": "./pyrightconfig.json",
        "exclude": [".venv", ".ai"],
    }
