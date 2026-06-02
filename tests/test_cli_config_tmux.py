from pathlib import Path

from typer.testing import CliRunner

from stackops.scripts.python.devops import get_app
from stackops.utils.path_reference import get_path_reference_path


def _tmux_asset_text() -> str:
    import stackops.settings.tmux as tmux_assets

    return get_path_reference_path(module=tmux_assets, path_reference=tmux_assets.TMUX_CONF_LOCAL_PATH_REFERENCE).read_text(encoding="utf-8")


def test_devops_config_terminal_help_lists_tmux_style_command() -> None:
    result = CliRunner().invoke(get_app(), ["c", "t", "--help"], env={"COLUMNS": "220"})

    assert result.exit_code == 0, result.output
    assert "tmux-style" in result.output
    assert "⭐ <r> Select starship prompt theme" in result.output
    assert "🎨 <t> Style tmux through the Oh My Tmux framework" in result.output
    assert "Style tmux through the Oh My Tmux framework" in result.output


def test_tmux_style_help_lists_framework_subcommands() -> None:
    result = CliRunner().invoke(get_app(), ["c", "t", "tmux-style", "--help"], env={"COLUMNS": "220"})

    assert result.exit_code == 0, result.output
    assert "🎨 <t> Style tmux through the Oh My Tmux framework" in result.output
    assert "install-oh-my-tmux" in result.output
    assert "apply-stackops-local" in result.output
    assert "set-option" in result.output
    assert "preset" in result.output
    assert "reload" in result.output


def test_tmux_style_install_oh_my_tmux_delegates_to_shared_installer(monkeypatch) -> None:
    from stackops.utils.installer_utils import installer_cli

    calls: list[dict[str, object]] = []

    def fake_main_installer_cli(**kwargs: object) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(installer_cli, "main_installer_cli", fake_main_installer_cli)

    result = CliRunner().invoke(get_app(), ["c", "t", "tmux-style", "install-oh-my-tmux", "--update"])

    assert result.exit_code == 0, result.output
    assert calls == [
        {
            "which": "oh-my-tmux",
            "group": False,
            "interactive": False,
            "explore": False,
            "update": True,
            "version": None,
        }
    ]


def test_tmux_style_short_alias_t_dispatches_to_tmux_group(monkeypatch) -> None:
    from stackops.utils.installer_utils import installer_cli

    calls: list[dict[str, object]] = []

    def fake_main_installer_cli(**kwargs: object) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(installer_cli, "main_installer_cli", fake_main_installer_cli)

    result = CliRunner().invoke(get_app(), ["c", "t", "t", "i"])

    assert result.exit_code == 0, result.output
    assert calls and calls[0]["which"] == "oh-my-tmux"


def test_tmux_style_apply_stackops_local_writes_home_local_config_by_default() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        home = Path.cwd()
        env = {"HOME": str(home), "XDG_CONFIG_HOME": str(home / ".config")}

        result = runner.invoke(get_app(), ["c", "t", "tmux-style", "apply-stackops-local"], env=env)

        assert result.exit_code == 0, result.output
        local_config = home / ".tmux.conf.local"
        assert local_config.read_text(encoding="utf-8") == _tmux_asset_text()


def test_tmux_style_set_option_updates_existing_oh_my_tmux_variable() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        home = Path.cwd()
        env = {"HOME": str(home), "XDG_CONFIG_HOME": str(home / ".config")}
        runner.invoke(get_app(), ["c", "t", "tmux-style", "apply-stackops-local"], env=env)

        result = runner.invoke(
            get_app(),
            ["c", "t", "tmux-style", "set-option", "tmux_conf_theme_colour_4", "#123456"],
            env=env,
        )

        assert result.exit_code == 0, result.output
        local_config = home / ".tmux.conf.local"
        text = local_config.read_text(encoding="utf-8")
        assert 'tmux_conf_theme_colour_4="#123456"' in text
        assert 'tmux_conf_theme_colour_4="#00afff"' not in text


def test_tmux_style_preset_updates_oh_my_tmux_colour_slots() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        home = Path.cwd()
        env = {"HOME": str(home), "XDG_CONFIG_HOME": str(home / ".config")}
        runner.invoke(get_app(), ["c", "t", "tmux-style", "apply-stackops-local"], env=env)

        result = runner.invoke(get_app(), ["c", "t", "tmux-style", "preset", "catppuccin-mocha"], env=env)

        assert result.exit_code == 0, result.output
        local_config = home / ".tmux.conf.local"
        text = local_config.read_text(encoding="utf-8")
        assert 'tmux_conf_theme_colour_1="#11111b"' in text
        assert 'tmux_conf_theme_colour_17="#cdd6f4"' in text


def test_tmux_style_apply_stackops_local_can_target_xdg_config() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        home = Path.cwd()
        env = {"HOME": str(home), "XDG_CONFIG_HOME": str(home / ".config")}

        result = runner.invoke(get_app(), ["c", "t", "tmux-style", "apply-stackops-local", "--location", "xdg"], env=env)

        assert result.exit_code == 0, result.output
        local_config = home / ".config" / "tmux" / "tmux.conf.local"
        assert local_config.read_text(encoding="utf-8") == _tmux_asset_text()
