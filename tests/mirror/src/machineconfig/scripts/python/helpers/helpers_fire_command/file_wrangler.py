from __future__ import annotations

from pathlib import Path

import pytest

from machineconfig.scripts.python.helpers.helpers_fire_command import file_wrangler


def test_parse_pyfile_lists_public_functions_only(tmp_path: Path) -> None:
    script_path = tmp_path.joinpath("sample_module.py")
    script_path.write_text(
        '''"""module docs"""

def usable(path: str) -> None:
    """callable"""
    return None

class Example:
    def method(self, value: int) -> None:
        return None

def __hidden__() -> None:
    return None
''',
        encoding="utf-8",
    )

    options, func_args = file_wrangler.parse_pyfile(str(script_path))

    assert options[0] == "RUN AS MAIN -- module docs"
    assert "usable -- path -- callable" in options
    assert len(options) == 2
    usable_index = options.index("usable -- path -- callable")
    usable_arg = func_args[usable_index][0]
    assert usable_arg.name == "path"
    assert usable_arg.type == "str"
    assert usable_arg.default is None


def test_find_repo_root_path_and_get_import_module_code(tmp_path: Path) -> None:
    repo_root = tmp_path.joinpath("repo")
    source_file = repo_root.joinpath("src", "demo", "tool.py")
    repo_root.joinpath(".git").mkdir(parents=True)
    source_file.parent.mkdir(parents=True)
    source_file.write_text("""print("tool")\n""", encoding="utf-8")

    assert file_wrangler.find_repo_root_path(str(source_file.parent)) == str(repo_root)
    assert file_wrangler.get_import_module_code(str(source_file)) == "from demo.tool import *"


@pytest.mark.parametrize(("platform_name", "expected_marker"), [("Windows", "SetEnvironmentVariable"), ("Linux", "export PYTHONPATH")])
def test_add_to_path_generates_platform_specific_script(monkeypatch: pytest.MonkeyPatch, platform_name: str, expected_marker: str) -> None:
    monkeypatch.setattr(file_wrangler.platform, "system", lambda: platform_name)

    script = file_wrangler.add_to_path(path_variable="PYTHONPATH", directory="/tmp/tools")

    assert "PYTHONPATH" in script
    assert "/tmp/tools" in script
    assert expected_marker in script
