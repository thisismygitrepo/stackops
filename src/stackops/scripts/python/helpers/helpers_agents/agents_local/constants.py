from typing import Final, Literal

CatalogSort = Literal["newest", "popular"]
CatalogCapability = Literal["tools", "thinking", "vision", "audio"]

OLLAMA_DEFAULT_HOST: Final[str] = "http://127.0.0.1:11434"
OLLAMA_DEFAULT_PORT: Final[int] = 11434
OLLAMA_TIMEOUT_SECONDS: Final[float] = 5.0
OLLAMA_CATALOG_URL: Final[str] = "https://ollama.com/library"
OLLAMA_CATALOG_TIMEOUT_SECONDS: Final[float] = 20.0
OLLAMA_DISCOVER_MIN_PARAMS: Final[float] = 0.0
OLLAMA_DISCOVER_MAX_PARAMS: Final[float] = 32.0
OLLAMA_DISCOVER_LIMIT: Final[int] = 20
OLLAMA_DISCOVER_SORT: Final[CatalogSort] = "newest"
OLLAMA_CATALOG_DOWNLOAD_WORKERS: Final[int] = 4
DOWNLOAD_SIZE_GB_FACTORS: Final[dict[str, float]] = {"B": 1e-9, "KB": 1e-6, "MB": 1e-3, "GB": 1.0, "TB": 1000.0}
HTML_VOID_ELEMENTS: Final[frozenset[str]] = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr",
})
