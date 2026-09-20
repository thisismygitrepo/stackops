from dataclasses import dataclass
from ipaddress import ip_address
from shutil import which
from typing import cast
from urllib.parse import urlsplit, urlunsplit

import requests

from stackops.scripts.python.helpers.helpers_agents.agents_local.constants import OLLAMA_DEFAULT_HOST, OLLAMA_DEFAULT_PORT


@dataclass(frozen=True)
class OllamaModel:
    name: str
    size: int
    family: str
    parameter_size: str
    quantization_level: str
    modified_at: str
    remote: bool


@dataclass(frozen=True)
class OllamaRunningModel:
    name: str
    size: int
    size_vram: int
    context_length: int | None
    expires_at: str


@dataclass(frozen=True)
class OllamaStatus:
    host: str
    cli_path: str | None
    version: str | None
    models: tuple[OllamaModel, ...] | None
    running_models: tuple[OllamaRunningModel, ...] | None
    errors: tuple[str, ...]


def _normalize_host(host: str) -> str:
    value = host.strip() or OLLAMA_DEFAULT_HOST
    if value == "ollama.com":
        value = "https://ollama.com"
    scheme, separator, address = value.partition("://")
    default_port = OLLAMA_DEFAULT_PORT
    if separator:
        default_port = 443 if scheme == "https" else 80
    else:
        scheme, address = "http", value
    authority, slash, path = address.partition("/")
    if authority.count(":") > 1 and not authority.startswith("["):
        authority = f"""[{ip_address(authority)}]"""
    parsed = urlsplit(f"""{scheme}://{authority}{slash}{path}""")
    if parsed.scheme not in {"http", "https"} or parsed.query or parsed.fragment or parsed.username is not None:
        raise ValueError("Ollama host must be an HTTP(S) address without credentials, query, or fragment")
    hostname = parsed.hostname or ("127.0.0.1" if authority.startswith(":") else "")
    if not hostname or any(character.isspace() for character in hostname):
        raise ValueError("Ollama host must include a valid hostname")
    hostname = {"0.0.0.0": "127.0.0.1", "::": "::1"}.get(hostname, hostname)
    if ":" in hostname:
        hostname = f"""[{hostname}]"""
    port = parsed.port if parsed.port is not None else default_port
    if port == 0:
        raise ValueError("Ollama host port must be between 1 and 65535")
    return urlunsplit((parsed.scheme, f"""{hostname}:{port}""", parsed.path.rstrip("/"), "", ""))


def _field[T](payload: dict[str, object], key: str, expected: type[T], missing: T | None) -> T:
    value = payload.get(key, missing)
    if not isinstance(value, expected) or isinstance(value, bool):
        raise ValueError(f"""{key} must be {expected.__name__}""")
    if isinstance(value, int) and value < 0:
        raise ValueError(f"""{key} must be non-negative""")
    return value


def _entries(payload: dict[str, object]) -> tuple[dict[str, object], ...]:
    values = payload.get("models")
    if not isinstance(values, list):
        raise ValueError("models must be a list")
    entries: list[dict[str, object]] = []
    for value in cast(list[object], values):
        if not isinstance(value, dict):
            raise ValueError("models entries must be objects")
        entries.append(cast(dict[str, object], value))
    return tuple(entries)


def _parse_models(payload: dict[str, object]) -> tuple[OllamaModel, ...]:
    models: list[OllamaModel] = []
    for entry in _entries(payload):
        raw_details = entry.get("details", {})
        if not isinstance(raw_details, dict):
            raise ValueError("model details must be an object")
        details = cast(dict[str, object], raw_details)
        remote_model = _field(entry, "remote_model", str, "")
        remote_host = _field(entry, "remote_host", str, "")
        models.append(OllamaModel(
            name=_field(entry, "name", str, None),
            size=_field(entry, "size", int, None),
            family=_field(details, "family", str, ""),
            parameter_size=_field(details, "parameter_size", str, ""),
            quantization_level=_field(details, "quantization_level", str, ""),
            modified_at=_field(entry, "modified_at", str, None),
            remote=bool(remote_model or remote_host),
        ))
    return tuple(models)


def _parse_running_models(payload: dict[str, object]) -> tuple[OllamaRunningModel, ...]:
    models: list[OllamaRunningModel] = []
    for entry in _entries(payload):
        context_length = None if entry.get("context_length") is None else _field(entry, "context_length", int, None)
        models.append(OllamaRunningModel(
            name=_field(entry, "name", str, None),
            size=_field(entry, "size", int, None),
            size_vram=_field(entry, "size_vram", int, None),
            context_length=context_length,
            expires_at=_field(entry, "expires_at", str, None),
        ))
    return tuple(models)


def collect_ollama_status(*, host: str, timeout: float) -> OllamaStatus:
    normalized_host = _normalize_host(host)
    version: str | None = None
    models: tuple[OllamaModel, ...] | None = None
    running_models: tuple[OllamaRunningModel, ...] | None = None
    errors: list[str] = []
    for endpoint in ("/api/version", "/api/tags", "/api/ps"):
        try:
            with requests.get(f"""{normalized_host}{endpoint}""", timeout=timeout) as response:
                response.raise_for_status()
                raw_payload = cast(object, response.json())
            if not isinstance(raw_payload, dict):
                raise ValueError("response must be an object")
            payload = cast(dict[str, object], raw_payload)
            match endpoint:
                case "/api/version":
                    version = _field(payload, "version", str, None)
                case "/api/tags":
                    models = _parse_models(payload)
                case "/api/ps":
                    running_models = _parse_running_models(payload)
        except requests.exceptions.JSONDecodeError:
            errors.append(f"""{endpoint}: invalid JSON response""")
        except requests.Timeout:
            errors.append(f"""{endpoint}: timed out after {timeout:g}s""")
        except requests.ConnectionError:
            errors.append(f"""{endpoint}: cannot connect to Ollama""")
        except requests.HTTPError as error:
            status = error.response.status_code if error.response is not None else "error"
            errors.append(f"""{endpoint}: HTTP {status}""")
        except requests.RequestException as error:
            errors.append(f"""{endpoint}: request failed ({type(error).__name__})""")
        except ValueError as error:
            errors.append(f"""{endpoint}: invalid response ({error})""")
    return OllamaStatus(
        host=normalized_host,
        cli_path=which("ollama"),
        version=version,
        models=models,
        running_models=running_models,
        errors=tuple(errors),
    )
