from stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile import _format_self_managed_mapper_path
from stackops.utils.source_of_truth import CONFIG_ROOT, DOTFILES_ROOT, resolve_source_of_truth_path


def test_resolve_source_of_truth_path_expands_known_roots() -> None:
    assert resolve_source_of_truth_path("CONFIG_ROOT/settings/app.json") == (CONFIG_ROOT / "settings" / "app.json").absolute()
    assert resolve_source_of_truth_path("DOTFILES_ROOT/creds/app/config.toml") == (DOTFILES_ROOT / "creds" / "app" / "config.toml").absolute()


def test_format_self_managed_mapper_path_uses_dotfiles_root_token() -> None:
    assert _format_self_managed_mapper_path(DOTFILES_ROOT / "creds" / "app" / "config.toml") == "DOTFILES_ROOT/creds/app/config.toml"
