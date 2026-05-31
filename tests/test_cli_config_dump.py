import json
from pathlib import Path

from typer.testing import CliRunner

from stackops.scripts.python.devops import get_app
from stackops.utils.path_reference import get_path_reference_path


def _profile_asset_text(path_reference: str) -> str:
    import stackops.profile as profile_assets

    return get_path_reference_path(module=profile_assets, path_reference=path_reference).read_text(encoding="utf-8")


def _secrets_asset_text(path_reference: str) -> str:
    import stackops.utils.schemas.secrets as secrets_assets

    return get_path_reference_path(module=secrets_assets, path_reference=path_reference).read_text(encoding="utf-8")


def test_devops_config_dump_help_lists_all_dump_targets() -> None:
    result = CliRunner().invoke(get_app(), ["c", "d", "--help"], env={"COLUMNS": "220"})

    assert result.exit_code == 0, result.output
    assert "[ve|layout|mapper_data|mapper_dotfiles|secrets|init|ia|live]" in result.output


def test_devops_config_dump_prints_live_from_github_script() -> None:
    result = CliRunner().invoke(get_app(), ["c", "d", "--which", "live"])

    assert result.exit_code == 0, result.output
    assert "git+https://github.com/thisismygitrepo/stackops" in result.output


def test_devops_config_dump_writes_mapper_data_example() -> None:
    import stackops.profile as profile_assets

    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(get_app(), ["c", "d", "--which", "mapper_data"])

        assert result.exit_code == 0, result.output
        output_dir = Path(".stackops/examples")
        assert (output_dir / "mapper_data.yaml").read_text(encoding="utf-8") == _profile_asset_text(
            profile_assets.MAPPER_DATA_PATH_REFERENCE
        )
        assert (output_dir / "mapper_data.schema.json").read_text(encoding="utf-8") == _profile_asset_text(
            profile_assets.MAPPER_DATA_SCHEMA_PATH_REFERENCE
        )


def test_devops_config_dump_writes_mapper_dotfiles_example() -> None:
    import stackops.profile as profile_assets

    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(get_app(), ["c", "d", "--which", "mapper_dotfiles"])

        assert result.exit_code == 0, result.output
        output_dir = Path(".stackops/examples")
        assert (output_dir / "mapper_dotfiles.yaml").read_text(encoding="utf-8") == _profile_asset_text(
            profile_assets.MAPPER_DOTFILES_PATH_REFERENCE
        )
        assert (output_dir / "mapper_dotfiles.schema.json").read_text(encoding="utf-8") == _profile_asset_text(
            profile_assets.MAPPER_DOTFILES_SCHEMA_PATH_REFERENCE
        )


def test_devops_config_dump_writes_secrets_example() -> None:
    import stackops.utils.schemas.secrets as secrets_assets

    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(get_app(), ["c", "d", "--which", "secrets"])

        assert result.exit_code == 0, result.output
        output_dir = Path(".stackops/examples")
        assert (output_dir / "secrets.example.json").read_text(encoding="utf-8") == _secrets_asset_text(
            secrets_assets.SECRETS_EXAMPLE_PATH_REFERENCE
        )
        assert (output_dir / "secrets.schema.json").read_text(encoding="utf-8") == _secrets_asset_text(
            secrets_assets.SECRETS_SCHEMA_PATH_REFERENCE
        )


def test_secrets_example_references_schema() -> None:
    import stackops.utils.schemas.secrets as secrets_assets

    example = json.loads(_secrets_asset_text(secrets_assets.SECRETS_EXAMPLE_PATH_REFERENCE))

    assert example["$schema"] == f"./{secrets_assets.SECRETS_SCHEMA_PATH_REFERENCE}"
