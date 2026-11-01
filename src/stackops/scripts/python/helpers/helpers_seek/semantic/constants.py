from pathlib import Path
from typing import Final


SEMANTIC_TOP_K: Final[int] = 10
SEMANTIC_PREVIEW_SIZE_PERCENT: Final[float] = 75.0
IDENTIFIER_HASH_LENGTH: Final[int] = 12

RG_NO_MATCH_EXIT_CODE: Final[int] = 1

SEMTOOLS_CONTEXT_LINES: Final[int] = 10
SEMTOOLS_OVERFETCH_FACTOR: Final[int] = 5
SEMTOOLS_WORKSPACE_PREFIX: Final[str] = "seek-"

INDEX_DIR_GITIGNORE_CONTENT: Final[str] = "*\n"

CK_NO_MATCH_EXIT_CODE: Final[int] = 1
CK_SEMANTIC_THRESHOLD: Final[float] = 0.0
CK_INDEX_DIR: Final[Path] = Path(".ck")

GREPAI_CONFIG_RELATIVE_PATH: Final[Path] = Path(".grepai") / "config.yaml"
GREPAI_INIT_PROVIDER: Final[str] = "ollama"
GREPAI_LOCAL_PROVIDERS: Final[tuple[str, ...]] = ("ollama", "lmstudio")
GREPAI_LOCAL_STORE: Final[str] = "gob"
LOOPBACK_HOSTS: Final[tuple[str, ...]] = ("localhost", "127.0.0.1", "::1")

QMD_COLLECTION_PREFIX: Final[str] = "seek-"
QMD_VECTOR_MIN_SCORE: Final[float] = -1.0
QMD_DEFAULT_EXTENSION: Final[str] = ".md"
QMD_INDEX_DIR: Final[Path] = Path(".qmd")
QMD_LOCAL_CONFIG_RELATIVE_PATHS: Final[tuple[Path, Path]] = (QMD_INDEX_DIR / "index.yml", QMD_INDEX_DIR / "index.yaml")
