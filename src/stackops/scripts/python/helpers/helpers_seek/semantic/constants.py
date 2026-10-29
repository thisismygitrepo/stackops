from pathlib import Path
from typing import Final


SEMANTIC_TOP_K: Final[int] = 10
SEMANTIC_PREVIEW_SIZE_PERCENT: Final[float] = 75.0
IDENTIFIER_HASH_LENGTH: Final[int] = 12

RG_NO_MATCH_EXIT_CODE: Final[int] = 1

SEMTOOLS_CONTEXT_LINES: Final[int] = 10
SEMTOOLS_OVERFETCH_FACTOR: Final[int] = 5
SEMTOOLS_WORKSPACE_PREFIX: Final[str] = "seek-"

CK_NO_MATCH_EXIT_CODE: Final[int] = 1

GREPAI_CONFIG_RELATIVE_PATH: Final[Path] = Path(".grepai") / "config.yaml"

QMD_COLLECTION_PREFIX: Final[str] = "seek-"
QMD_DEFAULT_EXTENSION: Final[str] = ".md"
QMD_LOCAL_CONFIG_RELATIVE_PATHS: Final[tuple[Path, Path]] = (Path(".qmd") / "index.yml", Path(".qmd") / "index.yaml")
