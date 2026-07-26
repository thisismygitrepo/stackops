import subprocess
from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_actions import write_env_handoff


@pytest.mark.parametrize(
    ("verbose", "expected_output"),
    (
        (False, "CLOUDFLARE_EMAIL=alex@example.com\n"),
        (
            True,
            "Defined env vars:\n  CLOUDFLARE_EMAIL\n  CLOUDFLARE_API_TOKEN\nCLOUDFLARE_EMAIL=alex@example.com\n",
        ),
    ),
)
def test_posix_handoff_reports_env_names_after_loading(
    verbose: bool,
    expected_output: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loader_path = tmp_path / "loader.sh"
    env_path = tmp_path / "loader.secrets.env.sh"
    monkeypatch.setenv("OP_PROGRAM_PATH", str(loader_path))

    write_env_handoff(
        {"CLOUDFLARE_EMAIL": "alex@example.com", "CLOUDFLARE_API_TOKEN": "api-token-secret"},
        verbose=verbose,
    )

    loader_text = loader_path.read_text(encoding="utf-8")
    result = subprocess.run(
        ["bash", "-c", '. "$1"\nprintf \'CLOUDFLARE_EMAIL=%s\\n\' "$CLOUDFLARE_EMAIL"', "stackops-test", str(loader_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == expected_output
    assert ("CLOUDFLARE_EMAIL" in loader_text) is verbose
    if verbose:
        assert loader_text.index('. "$_stackops_secret_env_file"') < loader_text.index("Defined env vars:")
    assert "alex@example.com" not in loader_text
    assert "api-token-secret" not in loader_text
    assert not env_path.exists()
