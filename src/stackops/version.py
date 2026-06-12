import tomllib
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path


def get_stackops_version() -> str:
    name = "stackops"
    try:
        return package_version(name)
    except PackageNotFoundError:
        pass
    root = Path(__file__).resolve().parents[2]
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        data: dict[str, object] = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        project = data.get("project")
        if isinstance(project, dict):
            project_version = project.get("version")
            if isinstance(project_version, str) and project_version:
                return project_version
    return "0.0.0"
