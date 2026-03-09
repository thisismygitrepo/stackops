from pathlib import Path

from machineconfig.scripts.python.helpers.helpers_agents.agents_impl import (
    resolve_agents_output_dir,
)


def test_resolve_agents_output_dir_uses_default_repo_path() -> None:
    repo_root = Path("/tmp/example-repo")

    agents_dir, job_name = resolve_agents_output_dir(
        repo_root=repo_root,
        agents_dir=None,
        job_name="agentsTrial",
    )

    assert agents_dir == repo_root / ".ai" / "agents" / "agentsTrial"
    assert job_name == "agentsTrial"


def test_resolve_agents_output_dir_does_not_append_job_name_to_explicit_dir(
    tmp_path: Path,
) -> None:
    explicit_dir = tmp_path / "agentsTrial"

    agents_dir, job_name = resolve_agents_output_dir(
        repo_root=tmp_path,
        agents_dir=str(explicit_dir),
        job_name="agentsTrial",
    )

    assert agents_dir == explicit_dir.resolve()
    assert job_name == "agentsTrial"


def test_resolve_agents_output_dir_uses_explicit_dir_name_when_job_name_missing(
    tmp_path: Path,
) -> None:
    explicit_dir = tmp_path / "custom-output"

    agents_dir, job_name = resolve_agents_output_dir(
        repo_root=tmp_path,
        agents_dir=str(explicit_dir),
        job_name=None,
    )

    assert agents_dir == explicit_dir.resolve()
    assert job_name == "custom-output"
