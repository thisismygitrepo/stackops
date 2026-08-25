from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorContext, DoctorOrigin, DoctorResource, DoctorResourceState
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.scanning import load_config_mapping


_ADMIN_CONFIG_PATH: Final[Path] = Path("/etc/codex/config.toml")


@dataclass(frozen=True)
class CodexConfigLayer:
    name: str
    origin: DoctorOrigin
    path: Path
    state: DoctorResourceState
    detail: str
    mapping: dict[str, object] | None


def _load_config_layer(*, name: str, origin: DoctorOrigin, path: Path, detail: str) -> CodexConfigLayer:
    resolved_path = path.expanduser().resolve(strict=False)
    if not resolved_path.exists():
        return CodexConfigLayer(name=name, origin=origin, path=resolved_path, state="missing", detail=detail, mapping=None)
    loaded = load_config_mapping(path=resolved_path, config_format="toml")
    if isinstance(loaded, str):
        error = loaded.replace("\n", " ")
        return CodexConfigLayer(
            name=name, origin=origin, path=resolved_path, state="configured", detail=f"{detail}; TOML could not be parsed: {error}", mapping=None
        )
    return CodexConfigLayer(name=name, origin=origin, path=resolved_path, state="active", detail=detail, mapping=loaded)


def config_layers(*, context: DoctorContext) -> tuple[CodexConfigLayer, ...]:
    project_layer_count = len(context.ancestor_directories)
    layers = [
        _load_config_layer(
            name="admin config.toml",
            origin="admin",
            path=_ADMIN_CONFIG_PATH,
            detail="administrator Codex configuration; lower precedence than user and project layers",
        ),
        _load_config_layer(
            name="user config.toml", origin="global", path=context.codex_home / "config.toml", detail="user Codex configuration; CODEX_HOME-aware"
        ),
    ]
    for layer_number, directory in enumerate(context.ancestor_directories, start=1):
        layers.append(
            _load_config_layer(
                name="project config.toml",
                origin="local",
                path=directory / ".codex" / "config.toml",
                detail=(
                    f"project layer {layer_number}/{project_layer_count} in root-to-working-directory precedence; "
                    "Codex loads project layers only for trusted projects"
                ),
            )
        )
    return tuple(layers)


def config_resources(*, layers: tuple[CodexConfigLayer, ...]) -> tuple[DoctorResource, ...]:
    return tuple(
        DoctorResource(
            kind="configuration", is_mcp=True, name=layer.name, origin=layer.origin, state=layer.state, path=layer.path, detail=layer.detail
        )
        for layer in layers
    )


def effective_fallback_names(*, layers: tuple[CodexConfigLayer, ...]) -> tuple[str, ...]:
    fallback_names: tuple[str, ...] = ()
    for layer in layers:
        if layer.mapping is None or "project_doc_fallback_filenames" not in layer.mapping:
            continue
        raw_names = layer.mapping["project_doc_fallback_filenames"]
        if isinstance(raw_names, list) and all(isinstance(name, str) and name.strip() != "" for name in raw_names):
            fallback_names = tuple(dict.fromkeys(cast(list[str], raw_names)))
        else:
            fallback_names = ()
    return fallback_names
