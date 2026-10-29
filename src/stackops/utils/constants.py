from pathlib import Path
from typing import Final

IS_REPO_DEVELOPER: Final[bool] = Path.home().joinpath("code", "stackops").is_dir()
STACKOPS_PYTHON_VERSION: Final[str] = "3.14"
