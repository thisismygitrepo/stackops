from pathlib import Path

from stackops.scripts.python.ai.initai_artifacts import write_text_artifact
from stackops.scripts.python.ai.initai_models import ArtifactChange
from stackops.scripts.python.ai.utils.shared import get_generic_instructions_path


PRIVATE_CONFIG_TEMPLATE_PATH = Path(__file__).with_name("config.toml")


def _read_private_config_template() -> str:
    return PRIVATE_CONFIG_TEMPLATE_PATH.read_text(encoding="utf-8")


def _ensure_private_config(repo_root: Path) -> ArtifactChange | None:
    return write_text_artifact(
        repo_root=repo_root,
        path=repo_root.joinpath(".codex/config.toml"),
        content=_read_private_config_template(),
        write_mode="if_missing",
    )


def build_configuration(repo_root: Path, add_private_config: bool, add_instructions: bool) -> tuple[ArtifactChange, ...]:
    changes: list[ArtifactChange] = []
    if add_private_config:
        change = _ensure_private_config(repo_root=repo_root)
        if change is not None:
            changes.append(change)

    if add_instructions:
        instructions_path = get_generic_instructions_path()
        change = write_text_artifact(
            repo_root=repo_root,
            path=repo_root.joinpath("AGENTS.md"),
            content=instructions_path.read_text(encoding="utf-8"),
            write_mode="always",
        )
        assert change is not None
        changes.append(change)
    return tuple(changes)
