import re
from dataclasses import dataclass
from html.parser import HTMLParser

import requests

from stackops.scripts.python.helpers.helpers_agents.agents_local.constants import DOWNLOAD_SIZE_GB_FACTORS, OLLAMA_CATALOG_URL


@dataclass(frozen=True)
class DownloadSize:
    minimum_gb: float
    maximum_gb: float


class _DownloadSizeParser(HTMLParser):
    def __init__(self, *, model_name: str, sizes: tuple[str, ...]) -> None:
        super().__init__(convert_charrefs=True)
        self.downloads: dict[str, DownloadSize] = {}
        self.tag_count: int = 0
        self._prefix = f"""/library/{model_name}:"""
        self._sizes = set(sizes)
        self._size: str | None = None
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attributes = dict(attrs)
        href = attributes.get("href") or ""
        if href.startswith(self._prefix) and "md:hidden" in (attributes.get("class") or "").split():
            self.tag_count += 1
            size = href.removeprefix(self._prefix)
            if size in self._sizes:
                self._size = size
                self._parts = []

    def handle_data(self, data: str) -> None:
        if self._size is not None:
            value = data.strip()
            if value:
                self._parts.append(value)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or self._size is None:
            return
        fields = " ".join(self._parts).split("•")
        if len(fields) > 1:
            amounts = re.findall(r"(\d+(?:\.\d+)?)\s*([KMGT]?B)\b", fields[1], flags=re.IGNORECASE)
            values = [float(amount) * DOWNLOAD_SIZE_GB_FACTORS[unit.upper()] for amount, unit in amounts]
            if values:
                self.downloads[self._size] = DownloadSize(minimum_gb=min(values), maximum_gb=max(values))
        self._size = None
        self._parts = []


def fetch_download_sizes(*, model_name: str, sizes: tuple[str, ...], timeout: float) -> dict[str, DownloadSize]:
    with requests.get(f"""{OLLAMA_CATALOG_URL}/{model_name}/tags""", timeout=timeout) as response:
        response.raise_for_status()
        parser = _DownloadSizeParser(model_name=model_name, sizes=sizes)
        parser.feed(response.text)
        parser.close()
    if not parser.tag_count:
        raise ValueError(f"""Ollama's tag page for {model_name} did not contain model tags; its page format may have changed.""")
    return parser.downloads
