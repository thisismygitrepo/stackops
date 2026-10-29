import math
import re
from dataclasses import dataclass
from shutil import which
from typing import cast

import requests

from stackops.scripts.python.helpers.helpers_agents.agents_local.constants import VLLM_DEFAULT_HOST, VLLM_DEFAULT_PORT
from stackops.scripts.python.helpers.helpers_agents.agents_local.server import normalize_host


@dataclass(frozen=True)
class VllmModel:
    name: str
    root: str | None
    parent: str | None
    max_model_len: int | None


@dataclass(frozen=True)
class VllmMetrics:
    running_requests: float | None
    waiting_requests: float | None
    peak_kv_cache_usage: float | None


@dataclass(frozen=True)
class VllmStatus:
    host: str
    cli_path: str | None
    healthy: bool
    version: str | None
    models: tuple[VllmModel, ...] | None
    metrics: VllmMetrics | None
    errors: tuple[str, ...]


def _parse_models(payload: dict[str, object]) -> tuple[VllmModel, ...]:
    entries = payload.get("data")
    if not isinstance(entries, list):
        raise ValueError("data must be a list")
    models: list[VllmModel] = []
    for raw_entry in cast(list[object], entries):
        if not isinstance(raw_entry, dict):
            raise ValueError("data entries must be objects")
        entry = cast(dict[str, object], raw_entry)
        name = entry.get("id")
        root = entry.get("root")
        parent = entry.get("parent")
        context = entry.get("max_model_len")
        if not isinstance(name, str) or not name:
            raise ValueError("model id must be a non-empty string")
        if root is not None and not isinstance(root, str):
            raise ValueError("model root must be a string or null")
        if parent is not None and not isinstance(parent, str):
            raise ValueError("model parent must be a string or null")
        if context is not None and (not isinstance(context, int) or isinstance(context, bool) or context < 0):
            raise ValueError("max_model_len must be a non-negative integer or null")
        models.append(VllmModel(name=name, root=root, parent=parent, max_model_len=context))
    return tuple(models)


def _parse_metrics(payload: str) -> VllmMetrics:
    samples: dict[str, list[float]] = {
        "vllm:num_requests_running": [], "vllm:num_requests_waiting": [], "vllm:kv_cache_usage_perc": [],
    }
    for raw_line in payload.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        name = line.partition("{")[0].split(maxsplit=1)[0]
        if name not in samples:
            continue
        match = re.fullmatch(r"[^\s{]+(?:\{.*\})?\s+(\S+)(?:\s+\d+)?", line)
        if match is None:
            raise ValueError(f"""invalid {name} metric""")
        value = float(match.group(1))
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"""{name} must be finite and non-negative""")
        samples[name].append(value)
    running = samples["vllm:num_requests_running"]
    waiting = samples["vllm:num_requests_waiting"]
    cache = samples["vllm:kv_cache_usage_perc"]
    return VllmMetrics(
        running_requests=sum(running) if running else None,
        waiting_requests=sum(waiting) if waiting else None,
        peak_kv_cache_usage=max(cache) if cache else None,
    )


def collect_vllm_status(*, host: str, timeout: float, api_key: str | None) -> VllmStatus:
    normalized_host = normalize_host(
        host=host, default_host=VLLM_DEFAULT_HOST, default_port=VLLM_DEFAULT_PORT, backend="vLLM",
    ).removesuffix("/v1")
    headers = {} if not api_key else {"Authorization": f"""Bearer {api_key}"""}
    healthy = False
    version: str | None = None
    models: tuple[VllmModel, ...] | None = None
    metrics: VllmMetrics | None = None
    errors: list[str] = []
    for endpoint in ("/health", "/version", "/v1/models", "/metrics"):
        try:
            with requests.get(f"""{normalized_host}{endpoint}""", headers=headers, timeout=timeout) as response:
                response.raise_for_status()
                if endpoint == "/health":
                    healthy = True
                    continue
                if endpoint == "/metrics":
                    metrics = _parse_metrics(response.text)
                    continue
                raw_payload = cast(object, response.json())
            if not isinstance(raw_payload, dict):
                raise ValueError("response must be an object")
            payload = cast(dict[str, object], raw_payload)
            if endpoint == "/version":
                raw_version = payload.get("version")
                if not isinstance(raw_version, str) or not raw_version:
                    raise ValueError("version must be a non-empty string")
                version = raw_version
            else:
                models = _parse_models(payload)
        except requests.exceptions.JSONDecodeError:
            errors.append(f"""{endpoint}: invalid JSON response""")
        except requests.Timeout:
            errors.append(f"""{endpoint}: timed out after {timeout:g}s""")
        except requests.ConnectionError:
            errors.append(f"""{endpoint}: cannot connect to vLLM""")
        except requests.HTTPError as error:
            status = error.response.status_code if error.response is not None else "error"
            hint = "; check --api-key / VLLM_API_KEY" if status in (401, 403) else ""
            errors.append(f"""{endpoint}: HTTP {status}{hint}""")
        except requests.RequestException as error:
            errors.append(f"""{endpoint}: request failed ({type(error).__name__})""")
        except ValueError as error:
            errors.append(f"""{endpoint}: invalid response ({error})""")
    return VllmStatus(
        host=normalized_host, cli_path=which("vllm"), healthy=healthy, version=version,
        models=models, metrics=metrics, errors=tuple(errors),
    )
