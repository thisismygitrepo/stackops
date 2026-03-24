from pathlib import Path

from machineconfig.scripts.python.ai.utils.shared import get_generic_instructions_path


PRIVATE_CONFIG_TEMPLATE_PATH = Path(__file__).with_name("config.toml")


def _read_private_config_template() -> str:
    return PRIVATE_CONFIG_TEMPLATE_PATH.read_text(encoding="utf-8")


def _ensure_private_config(repo_root: Path) -> None:
    codex_dir = repo_root.joinpath(".codex")
    codex_dir.mkdir(parents=True, exist_ok=True)
    config_path = codex_dir.joinpath("config.toml")
    if config_path.exists():
        return
    config_path.write_text(data=_read_private_config_template(), encoding="utf-8")


def build_configuration(repo_root: Path, add_private_config: bool, add_instructions: bool) -> None:
    if add_private_config:
        _ensure_private_config(repo_root=repo_root)

    if add_instructions:
        instructions_path = get_generic_instructions_path()
        repo_root.joinpath("AGENTS.md").write_text(data=instructions_path.read_text(encoding="utf-8"), encoding="utf-8")
