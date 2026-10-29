from dataclasses import dataclass
from typing import assert_never, cast

import requests

from stackops.scripts.python.helpers.helpers_agents.agents_local.constants import (
    HUGGING_FACE_MODELS_URL,
    VLLM_CATALOG_PAGE_SIZE,
    CatalogCapability,
    CatalogSort,
)


@dataclass(frozen=True)
class VllmCatalogModel:
    name: str
    parameters: int
    downloads: int
    task: str
    updated: str


def discover_vllm_models(
    *, min_params: float, max_params: float, sort: CatalogSort, limit: int, query: str, capability: CatalogCapability | None, timeout: float,
) -> tuple[VllmCatalogModel, ...]:
    if capability is not None:
        raise ValueError("--capability is available for Ollama; Hugging Face does not provide equivalent capability metadata for vLLM.")

    match sort:
        case "trending":
            hub_sort = "trendingScore"
        case "popular":
            hub_sort = "downloads"
        case "newest":
            raise ValueError("--sort newest is available for Ollama; Hugging Face creation order lists unvetted uploads with no downloads. Use trending or popular.")
        case _ as unreachable:
            assert_never(unreachable)

    params: dict[str, str | int | list[str]] = {
        "apps": "vllm",
        "num_parameters": f"""min:{min_params:g}B,max:{max_params:g}B""",
        "sort": hub_sort,
        "direction": -1,
        "limit": VLLM_CATALOG_PAGE_SIZE,
        "expand": ["safetensors", "downloads", "pipeline_tag", "lastModified"],
    }
    if search := query.strip():
        params["search"] = search

    matches: list[VllmCatalogModel] = []
    url: str | None = HUGGING_FACE_MODELS_URL
    while url is not None:
        with requests.get(url, params=params, timeout=timeout) as response:
            response.raise_for_status()
            payload = cast(object, response.json())
            url = response.links.get("next", {}).get("url")
        params = {}
        if not isinstance(payload, list):
            raise ValueError("Hugging Face model catalog must be a list.")
        for raw_entry in cast(list[object], payload):
            if not isinstance(raw_entry, dict):
                raise ValueError("Hugging Face model catalog entries must be objects.")
            entry = cast(dict[str, object], raw_entry)
            safetensors = entry.get("safetensors")
            if safetensors is None:
                continue
            if not isinstance(safetensors, dict):
                raise ValueError("Hugging Face safetensors metadata must be an object.")
            parameters = cast(dict[str, object], safetensors).get("total")
            if parameters is None:
                continue
            if not isinstance(parameters, int) or isinstance(parameters, bool) or parameters < 0:
                raise ValueError("Hugging Face parameter counts must be non-negative integers.")
            if not min_params <= parameters / 1e9 <= max_params:
                continue
            name = entry.get("id")
            downloads = entry.get("downloads")
            task = entry.get("pipeline_tag")
            updated = entry.get("lastModified")
            if not isinstance(name, str) or not name:
                raise ValueError("Hugging Face model IDs must be non-empty strings.")
            if search and search.casefold() not in name.casefold():
                continue
            if not isinstance(downloads, int) or isinstance(downloads, bool) or downloads < 0:
                raise ValueError("Hugging Face download counts must be non-negative integers.")
            if task is not None and not isinstance(task, str):
                raise ValueError("Hugging Face model tasks must be strings.")
            if updated is not None and not isinstance(updated, str):
                raise ValueError("Hugging Face modification dates must be strings.")
            matches.append(VllmCatalogModel(
                name=name,
                parameters=parameters,
                downloads=downloads,
                task=task or "-",
                updated=updated or "-",
            ))
            if len(matches) == limit:
                return tuple(matches)
    return tuple(matches)
