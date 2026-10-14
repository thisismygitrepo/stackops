from datetime import date
from pathlib import Path
import subprocess

from git import Repo
import pytest

from stackops.scripts.python.helpers.helpers_devops import stackops_release


def initialize_repository(repo_root: Path, files: dict[str, bytes]) -> Repo:
    repository = Repo.init(repo_root, initial_branch="main")
    contents = {"pyproject.toml": b'[project]\nname = "stackops"\nversion = "26.9.2"\n', "uv.lock": b"version = 1\n", **files}
    for name, content in contents.items():
        path = repo_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    repository.index.add(list(contents))
    return repository


def mock_uv(monkeypatch: pytest.MonkeyPatch, failure: str | None) -> list[list[str]]:
    commands: list[list[str]] = []
    original_run = subprocess.run

    def run(command: list[str], cwd: Path, check: bool, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if command[0] != "uv":
            return original_run(command, cwd=cwd, check=check, capture_output=True, text=True)
        commands.append(command)
        if command[1] == failure:
            raise subprocess.CalledProcessError(returncode=1, cmd=command)
        if command[1] == "version":
            pyproject = cwd / "pyproject.toml"
            pyproject.write_bytes(pyproject.read_bytes().replace(b'"26.9.2"', b'"26.9.3"'))
        elif command == ["uv", "sync"]:
            cwd.joinpath("uv.lock").write_bytes(b"version = 1\nrevision = 2\n")
        else:
            raise AssertionError(f"Unexpected uv invocation: {command}")
        return subprocess.CompletedProcess(command, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(stackops_release.subprocess, "run", run)
    return commands


def test_bump_refreshes_stale_tracked_references_and_preserves_unmanaged_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = b"""STACKOPS_VERSION: str = '26.9.1'\r\nrequirements = ["stackops>=26.9.2", "stackops[plot,dev]>=26.8"]\r\n"""
    untouched = b'values = ["my-stackops>=26.9.2", "stackops>=26.9.2a1", "stackops>=26.9.2.post1"]\n'
    repository = initialize_repository(
        repo_root=tmp_path,
        files={
            "src/stackops/runtime.py": source,
            "src/stackops/unrelated.py": untouched,
            "scripts/setup.sh": b'uvx --from "stackops>=26.9.1" devops\n',
            "jobs/setup.ps1": b'uvx --from "stackops[plot]>=26.7" devops\n',
            "Dockerfile.test": b'RUN uv pip install "stackops>=26.9.1"\n',
            "tests/test_versions.py": source,
            "src/manual/test_versions.py": source,
            "src/stackops/.venv/ignored.py": source,
        },
    )
    tmp_path.joinpath("src/stackops/untracked.py").write_bytes(source)
    external = tmp_path / "external.py"
    external.write_bytes(source)
    tmp_path.joinpath("src/stackops/linked.py").symlink_to(external)
    repository.index.add(["src/stackops/linked.py"])
    commands = mock_uv(monkeypatch=monkeypatch, failure=None)

    result = stackops_release.bump_stackops_version(repo_root=tmp_path, today=date(2026, 9, 13))

    assert (result.previous_version, result.version) == ("26.9.2", "26.9.3")
    assert set(result.changed_files) == {
        Path("pyproject.toml"),
        Path("uv.lock"),
        Path("src/stackops/runtime.py"),
        Path("scripts/setup.sh"),
        Path("jobs/setup.ps1"),
        Path("Dockerfile.test"),
    }
    assert commands == [["uv", "version", "26.9.3", "--no-sync"], ["uv", "sync"]]
    updated = tmp_path.joinpath("src/stackops/runtime.py").read_bytes()
    assert updated == source.replace(b"26.9.1", b"26.9.3").replace(b"26.9.2", b"26.9.3").replace(b"26.8", b"26.9.3")
    assert tmp_path.joinpath("src/stackops/unrelated.py").read_bytes() == untouched
    for name in (
        "tests/test_versions.py",
        "src/manual/test_versions.py",
        "src/stackops/.venv/ignored.py",
        "src/stackops/untracked.py",
        "external.py",
    ):
        assert tmp_path.joinpath(name).read_bytes() == source


def test_source_decoding_errors_are_detected_before_uv_mutation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    initialize_repository(repo_root=tmp_path, files={"src/stackops/broken.py": b"\xff"})
    commands = mock_uv(monkeypatch=monkeypatch, failure=None)
    original = tmp_path.joinpath("pyproject.toml").read_bytes()

    with pytest.raises(UnicodeDecodeError):
        stackops_release.bump_stackops_version(repo_root=tmp_path, today=date(2026, 9, 13))

    assert commands == []
    assert tmp_path.joinpath("pyproject.toml").read_bytes() == original


def test_symlinked_source_directory_is_never_followed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    content = b'REQUIREMENT = "stackops>=26.9.1"\n'
    initialize_repository(repo_root=tmp_path, files={"src/stackops/linked/module.py": content})
    target = tmp_path / "elsewhere"
    tmp_path.joinpath("src/stackops/linked").rename(target)
    tmp_path.joinpath("src/stackops/linked").symlink_to(target, target_is_directory=True)
    mock_uv(monkeypatch=monkeypatch, failure=None)

    result = stackops_release.bump_stackops_version(repo_root=tmp_path, today=date(2026, 9, 13))

    assert target.joinpath("module.py").read_bytes() == content
    assert result.changed_files == (Path("pyproject.toml"), Path("uv.lock"))


@pytest.mark.parametrize("invalid", ["missing", "wrong-project", "nested", "bare", "invalid-toml"])
def test_repository_detection_requires_stackops_checkout_root(tmp_path: Path, invalid: str) -> None:
    repo_root = tmp_path / "repo"
    if invalid == "bare":
        Repo.init(repo_root, bare=True)
        repo_root.joinpath("pyproject.toml").write_text('[project]\nname = "stackops"\n', encoding="utf-8")
    elif invalid != "missing":
        files = {"nested/pyproject.toml": b'[project]\nname = "stackops"\n'}
        if invalid == "wrong-project":
            files["pyproject.toml"] = b'[project]\nname = "other"\nversion = "26.9.2"\n'
        elif invalid == "invalid-toml":
            files["pyproject.toml"] = b"[broken"
        initialize_repository(repo_root=repo_root, files=files)
        if invalid == "nested":
            repo_root = repo_root / "nested"

    assert not stackops_release.is_stackops_repository(repo_root=repo_root)
    with pytest.raises(ValueError, match="Expected a StackOps Git checkout"):
        stackops_release.bump_stackops_version(repo_root=repo_root, today=date(2026, 9, 13))


@pytest.mark.parametrize("metadata", ["pyproject.toml", "uv.lock"])
def test_symlinked_metadata_is_rejected(tmp_path: Path, metadata: str, monkeypatch: pytest.MonkeyPatch) -> None:
    initialize_repository(repo_root=tmp_path, files={})
    external = tmp_path / "outside"
    tmp_path.joinpath(metadata).rename(external)
    tmp_path.joinpath(metadata).symlink_to(external)
    commands = mock_uv(monkeypatch=monkeypatch, failure=None)

    with pytest.raises(ValueError):
        stackops_release.bump_stackops_version(repo_root=tmp_path, today=date(2026, 9, 13))

    assert commands == []


@pytest.mark.parametrize("failure", ["version", "sync"])
def test_uv_failure_stops_release(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str) -> None:
    source = b'REQUIREMENT = "stackops>=26.9.1"\n'
    initialize_repository(repo_root=tmp_path, files={"src/stackops/runtime.py": source})
    commands = mock_uv(monkeypatch=monkeypatch, failure=failure)

    with pytest.raises(subprocess.CalledProcessError):
        stackops_release.bump_stackops_version(repo_root=tmp_path, today=date(2026, 9, 13))

    expected_commands = [["uv", "version", "26.9.3", "--no-sync"]]
    if failure == "sync":
        expected_commands.append(["uv", "sync"])
        source = source.replace(b"26.9.1", b"26.9.3")
    assert commands == expected_commands
    assert tmp_path.joinpath("src/stackops/runtime.py").read_bytes() == source
