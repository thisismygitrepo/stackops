

import runpy
from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if candidate.joinpath("pyproject.toml").is_file():
            return candidate
    raise AssertionError(f"Could not find repo root from {start}")


def _get_module_path(test_file: Path) -> Path:
    repo_root = _find_repo_root(start=test_file)
    mirror_root = repo_root.joinpath("tests", "mirror")
    return repo_root.joinpath(test_file.relative_to(mirror_root))


def test_path_references_target_existing_files() -> None:
    module_path = _get_module_path(test_file=Path(__file__).resolve())
    namespace: dict[str, object] = runpy.run_path(str(module_path))
    expected_references: tuple[tuple[str, str], ...] = (
        ("BR_PATH_REFERENCE", "br.sh"),
        ("BROOTCD_PATH_REFERENCE", "brootcd.ps1"),
        ("CONF_PATH_REFERENCE", "conf.toml"),
    )

    for variable_name, expected_relative_path in expected_references:
        path_reference_object = namespace[variable_name]
        assert isinstance(path_reference_object, str)
        path_reference = path_reference_object
        assert path_reference == expected_relative_path
        assert module_path.parent.joinpath(path_reference).is_file()
