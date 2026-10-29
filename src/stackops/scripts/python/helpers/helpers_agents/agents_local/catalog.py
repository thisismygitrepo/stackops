import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from html.parser import HTMLParser
from typing import Literal

import requests

from stackops.scripts.python.helpers.helpers_agents.agents_local.catalog_downloads import DownloadSize, fetch_download_sizes
from stackops.scripts.python.helpers.helpers_agents.agents_local.constants import (
    HTML_VOID_ELEMENTS,
    OLLAMA_CATALOG_DOWNLOAD_WORKERS,
    OLLAMA_CATALOG_URL,
    CatalogCapability,
    CatalogSort,
)

type _CatalogField = Literal["description", "sizes", "capabilities", "metadata"]


@dataclass(frozen=True)
class CatalogModel:
    name: str
    description: str
    sizes: tuple[str, ...]
    download_sizes_gb: dict[str, DownloadSize]
    capabilities: tuple[str, ...]
    pulls: str
    updated: str


class _CatalogParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.models: list[CatalogModel] = []
        self._name: str | None = None
        self._fields: list[_CatalogField | None] = []
        self._content: dict[_CatalogField, list[str]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "a" and re.fullmatch(r"/library/[\w.-]+", attributes.get("href") or ""):
            self._name = (attributes["href"] or "").removeprefix("/library/")
            self._content = {"description": [], "sizes": [], "capabilities": [], "metadata": []}
            self._fields = []
        if self._name is None or tag in HTML_VOID_ELEMENTS:
            return
        classes = (attributes.get("class") or "").split()
        field: _CatalogField | None = self._fields[-1] if self._fields else None
        if tag == "p":
            field = "metadata" if self._content["description"] else "description"
        elif tag == "span" and "bg-[#ddf4ff]" in classes:
            field = "sizes"
        elif tag == "span" and {"bg-indigo-50", "bg-cyan-50"}.intersection(classes):
            field = "capabilities"
        self._fields.append(field)

    def handle_data(self, data: str) -> None:
        if self._fields and (field := self._fields[-1]) is not None:
            value = " ".join(data.split())
            if value:
                self._content[field].append(value)

    def handle_endtag(self, tag: str) -> None:
        if self._name is None or tag in HTML_VOID_ELEMENTS:
            return
        if self._fields:
            self._fields.pop()
        if tag == "a":
            metadata = " ".join(self._content["metadata"])
            pulls = re.search(r"([\d.,]+[KMB]?)\s+Pulls\b", metadata)
            updated = re.search(r"Updated\s+(.+)$", metadata)
            self.models.append(CatalogModel(
                name=self._name,
                description=" ".join(self._content["description"]),
                sizes=tuple(self._content["sizes"]),
                download_sizes_gb={},
                capabilities=tuple(self._content["capabilities"]),
                pulls=pulls.group(1) if pulls else "-",
                updated=updated.group(1) if updated else "-",
            ))
            self._name = None
            self._fields = []


def discover_models(
    *, min_params: float, max_params: float, sort: CatalogSort, limit: int, query: str, capability: CatalogCapability | None, timeout: float,
) -> tuple[CatalogModel, ...]:
    with requests.get(OLLAMA_CATALOG_URL, params={"sort": sort}, timeout=timeout) as response:
        response.raise_for_status()
        parser = _CatalogParser()
        parser.feed(response.text)
        parser.close()
    if not parser.models:
        raise ValueError("Ollama's catalog did not contain model entries; its page format may have changed.")

    matches: list[CatalogModel] = []
    search = query.strip().casefold()
    for model in parser.models:
        if {"embedding", "decision"}.intersection(model.capabilities):
            continue
        if capability is not None and capability not in model.capabilities:
            continue
        if search and search not in f"""{model.name} {model.description}""".casefold():
            continue
        sizes: list[str] = []
        for size in model.sizes:
            if match := re.fullmatch(r"(\d+(?:\.\d+)?)([bm])", size.casefold()):
                parameters = float(match.group(1)) / (1000 if match.group(2) == "m" else 1)
                if min_params <= parameters <= max_params:
                    sizes.append(size)
        if sizes:
            matches.append(replace(model, sizes=tuple(sizes)))
        if len(matches) == limit:
            break
    with ThreadPoolExecutor(max_workers=OLLAMA_CATALOG_DOWNLOAD_WORKERS) as executor:
        downloads = [
            executor.submit(fetch_download_sizes, model_name=model.name, sizes=model.sizes, timeout=timeout)
            for model in matches
        ]
        return tuple(
            replace(model, download_sizes_gb=download.result())
            for model, download in zip(matches, downloads, strict=True)
        )
