import json
from pathlib import Path

from typer.testing import CliRunner

from stackops.scripts.python.devops import get_app
from stackops.utils.path_reference import get_path_reference_path


def _profile_asset_text(path_reference: str) -> str:
    import stackops.utils.schemas.mapper as mapper_assets

    return get_path_reference_path(module=mapper_assets, path_reference=path_reference).read_text(encoding="utf-8")


def _secrets_asset_text(path_reference: str) -> str:
    import stackops.utils.schemas.secrets as secrets_assets

    return get_path_reference_path(module=secrets_assets, path_reference=path_reference).read_text(encoding="utf-8")


def _config_asset_text(path_reference: str) -> str:
    import stackops.utils.schemas.config as config_assets

    return get_path_reference_path(module=config_assets, path_reference=path_reference).read_text(encoding="utf-8")


def test_devops_config_dump_help_lists_all_dump_targets() -> None:
    result = CliRunner().invoke(get_app(), ["c", "d", "--help"], env={"COLUMNS": "220"})

    assert result.exit_code == 0, result.output
    assert "[ve|layout|data|dotfiles|secrets|config|init|ia|live]" in result.output
    assert "mapper_data" not in result.output
    assert "mapper_dotfiles" not in result.output
    assert "--data" in result.output
    assert "-d" in result.output
    assert "--schema" in result.output
    assert "-s" in result.output
    assert "--default-path" in result.output
    assert "-p" in result.output
    assert "--force" in result.output
    assert "-f" in result.output


def test_devops_config_dump_prints_live_from_github_script() -> None:
    result = CliRunner().invoke(get_app(), ["c", "d", "--which", "live"])

    assert result.exit_code == 0, result.output
    assert "git+https://github.com/thisismygitrepo/stackops" in result.output


def test_devops_config_dump_writes_data_example() -> None:
    import stackops.utils.schemas.mapper as mapper_assets

    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(get_app(), ["c", "d", "--which", "data"])

        assert result.exit_code == 0, result.output
        output_dir = Path(".stackops/examples")
        assert (output_dir / "data.yaml").read_text(encoding="utf-8") == _profile_asset_text(
            mapper_assets.MAPPER_DATA_PATH_REFERENCE
        )
        assert (output_dir / "data.schema.json").read_text(encoding="utf-8") == _profile_asset_text(
            mapper_assets.MAPPER_DATA_SCHEMA_PATH_REFERENCE
        )


def test_devops_config_dump_writes_dotfiles_example() -> None:
    import stackops.utils.schemas.mapper as mapper_assets

    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(get_app(), ["c", "d", "--which", "dotfiles"])

        assert result.exit_code == 0, result.output
        output_dir = Path(".stackops/examples")
        assert (output_dir / "dotfiles.yaml").read_text(encoding="utf-8") == _profile_asset_text(
            mapper_assets.MAPPER_DOTFILES_PATH_REFERENCE
        )
        assert (output_dir / "dotfiles.schema.json").read_text(encoding="utf-8") == _profile_asset_text(
            mapper_assets.MAPPER_DOTFILES_SCHEMA_PATH_REFERENCE
        )


def test_devops_config_dump_writes_secrets_example() -> None:
    import stackops.utils.schemas.secrets as secrets_assets

    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(get_app(), ["c", "d", "--which", "secrets"])

        assert result.exit_code == 0, result.output
        output_dir = Path(".stackops/secrets")
        assert (output_dir / "secrets.json").read_text(encoding="utf-8") == _secrets_asset_text(
            secrets_assets.SECRETS_EXAMPLE_PATH_REFERENCE
        )
        assert (output_dir / "secrets.schema.json").read_text(encoding="utf-8") == _secrets_asset_text(
            secrets_assets.SECRETS_SCHEMA_PATH_REFERENCE
        )


def test_devops_config_dump_writes_config_example() -> None:
    import stackops.utils.schemas.config as config_assets

    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(get_app(), ["c", "d", "--which", "config"])

        assert result.exit_code == 0, result.output
        output_dir = Path(".stackops/config")
        assert (output_dir / "config.json").read_text(encoding="utf-8") == _config_asset_text(config_assets.CONFIG_PATH_REFERENCE)
        assert (output_dir / "config.schema.json").read_text(encoding="utf-8") == _config_asset_text(
            config_assets.CONFIG_SCHEMA_PATH_REFERENCE
        )


def test_devops_config_dump_refuses_existing_data_without_force() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        output_dir = Path(".stackops/config")
        output_dir.mkdir(parents=True)
        data_path = output_dir / "config.json"
        data_path.write_text("existing config\n", encoding="utf-8")

        result = runner.invoke(get_app(), ["c", "d", "--which", "config"])

        assert result.exit_code == 1, result.output
        assert "Refusing to overwrite existing file(s)" in result.output
        assert "--force/-f" in result.output
        assert data_path.read_text(encoding="utf-8") == "existing config\n"
        assert not (output_dir / "config.schema.json").exists()


def test_devops_config_dump_refuses_existing_schema_without_force() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        output_dir = Path(".stackops/secrets")
        output_dir.mkdir(parents=True)
        schema_path = output_dir / "secrets.schema.json"
        schema_path.write_text("existing schema\n", encoding="utf-8")

        result = runner.invoke(get_app(), ["c", "d", "--which", "secrets"])

        assert result.exit_code == 1, result.output
        assert "Refusing to overwrite existing file(s)" in result.output
        assert "--force/-f" in result.output
        assert not (output_dir / "secrets.json").exists()
        assert schema_path.read_text(encoding="utf-8") == "existing schema\n"


def test_devops_config_dump_force_overwrites_existing_files() -> None:
    import stackops.utils.schemas.config as config_assets

    runner = CliRunner()
    with runner.isolated_filesystem():
        output_dir = Path(".stackops/config")
        output_dir.mkdir(parents=True)
        (output_dir / "config.json").write_text("existing config\n", encoding="utf-8")
        (output_dir / "config.schema.json").write_text("existing schema\n", encoding="utf-8")

        result = runner.invoke(get_app(), ["c", "d", "--which", "config", "-f"])

        assert result.exit_code == 0, result.output
        assert (output_dir / "config.json").read_text(encoding="utf-8") == _config_asset_text(config_assets.CONFIG_PATH_REFERENCE)
        assert (output_dir / "config.schema.json").read_text(encoding="utf-8") == _config_asset_text(
            config_assets.CONFIG_SCHEMA_PATH_REFERENCE
        )


def test_devops_config_dump_can_write_only_schema() -> None:
    import stackops.utils.schemas.config as config_assets

    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(get_app(), ["c", "d", "--which", "config", "-s"])

        assert result.exit_code == 0, result.output
        output_dir = Path(".stackops/config")
        assert not (output_dir / "config.json").exists()
        assert (output_dir / "config.schema.json").read_text(encoding="utf-8") == _config_asset_text(
            config_assets.CONFIG_SCHEMA_PATH_REFERENCE
        )


def test_devops_config_dump_can_write_only_data() -> None:
    import stackops.utils.schemas.secrets as secrets_assets

    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(get_app(), ["c", "d", "--which", "secrets", "-d"])

        assert result.exit_code == 0, result.output
        output_dir = Path(".stackops/secrets")
        assert (output_dir / "secrets.json").read_text(encoding="utf-8") == _secrets_asset_text(
            secrets_assets.SECRETS_EXAMPLE_PATH_REFERENCE
        )
        assert not (output_dir / "secrets.schema.json").exists()


def test_devops_config_dump_writes_config_to_default_path(monkeypatch, tmp_path: Path) -> None:
    import stackops.utils.schemas.config as config_assets
    from stackops.utils import source_of_truth

    config_path = tmp_path / "dotfiles" / "stackops" / "config" / "config.json"
    monkeypatch.setattr(source_of_truth, "DOTFILES_STACKOPS_CONFIG_PATH", config_path)

    result = CliRunner().invoke(get_app(), ["c", "d", "--which", "config", "-d", "-p"])

    assert result.exit_code == 0, result.output
    assert config_path.read_text(encoding="utf-8") == _config_asset_text(config_assets.CONFIG_PATH_REFERENCE)


def test_devops_config_dump_writes_secrets_schema_to_default_path(monkeypatch, tmp_path: Path) -> None:
    import stackops.utils.schemas.secrets as secrets_assets
    from stackops.utils import source_of_truth

    secrets_path = tmp_path / "dotfiles" / "stackops" / "secrets" / "secrets.json"
    monkeypatch.setattr(source_of_truth, "SECRETS_DOFILE", secrets_path)

    result = CliRunner().invoke(get_app(), ["c", "d", "--which", "secrets", "-s", "-p"])

    assert result.exit_code == 0, result.output
    assert not secrets_path.exists()
    assert (secrets_path.parent / "secrets.schema.json").read_text(encoding="utf-8") == _secrets_asset_text(
        secrets_assets.SECRETS_SCHEMA_PATH_REFERENCE
    )


def test_secrets_example_references_schema() -> None:
    import stackops.utils.schemas.secrets as secrets_assets

    example = json.loads(_secrets_asset_text(secrets_assets.SECRETS_EXAMPLE_PATH_REFERENCE))

    assert example["$schema"] == f"./{secrets_assets.SECRETS_SCHEMA_PATH_REFERENCE}"


def test_config_example_references_schema() -> None:
    import stackops.utils.schemas.config as config_assets

    example = json.loads(_config_asset_text(config_assets.CONFIG_PATH_REFERENCE))

    assert example["$schema"] == f"./{config_assets.CONFIG_SCHEMA_PATH_REFERENCE}"
