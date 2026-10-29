from typing import Final, Literal

CatalogSort = Literal["newest", "popular"]
CatalogCapability = Literal["tools", "thinking", "vision", "audio"]
LocalBackend = Literal["ollama", "vllm"]

LOCAL_DEFAULT_BACKEND: Final[LocalBackend] = "ollama"
VLLM_DEFAULT_HOST: Final[str] = "http://127.0.0.1:8000"
VLLM_DEFAULT_PORT: Final[int] = 8000
VLLM_BIND_HOST: Final[str] = "127.0.0.1"
VLLM_TIMEOUT_SECONDS: Final[float] = 5.0
VLLM_INSTALL_PYTHON: Final[str] = "3.13"
HUGGING_FACE_MODELS_URL: Final[str] = "https://huggingface.co/api/models"
HUGGING_FACE_HUB_URL: Final[str] = "https://huggingface.co"
VLLM_CATALOG_URL: Final[str] = "https://huggingface.co/models?apps=vllm"
VLLM_CATALOG_PAGE_SIZE: Final[int] = 100

OLLAMA_DEFAULT_HOST: Final[str] = "http://127.0.0.1:11434"
OLLAMA_DEFAULT_PORT: Final[int] = 11434
OLLAMA_TIMEOUT_SECONDS: Final[float] = 5.0
OLLAMA_CATALOG_URL: Final[str] = "https://ollama.com/library"
OLLAMA_CATALOG_TIMEOUT_SECONDS: Final[float] = 20.0
OLLAMA_DISCOVER_MIN_PARAMS: Final[float] = 20.0
OLLAMA_DISCOVER_MAX_PARAMS: Final[float] = 32.0
OLLAMA_DISCOVER_LIMIT: Final[int] = 20
OLLAMA_DISCOVER_SORT: Final[CatalogSort] = "newest"
OLLAMA_CATALOG_DOWNLOAD_WORKERS: Final[int] = 20
DOWNLOAD_SIZE_GB_FACTORS: Final[dict[str, float]] = {"B": 1e-9, "KB": 1e-6, "MB": 1e-3, "GB": 1.0, "TB": 1000.0}
HTML_VOID_ELEMENTS: Final[frozenset[str]] = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr",
})
