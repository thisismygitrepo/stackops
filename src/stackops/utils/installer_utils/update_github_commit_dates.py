import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict, cast
from urllib.parse import quote, urlsplit


INSTALLER_DATA_PATH = Path(__file__).resolve().parents[1].joinpath("schemas", "installer", "installer_data.json")
GITHUB_HOST = "github.com"


class CommitDateMetadata(TypedDict):
    lastCommitDate: str
    lastCommitDateCheckDate: str


def run_gh(args: list[str], failure_message: str) -> str:
    try:
        result = subprocess.run(["gh", *args], check=False, capture_output=True, text=True)
    except FileNotFoundError as error:
        raise RuntimeError("GitHub CLI was not found on PATH. Install `gh`, then run `gh auth login --hostname github.com`.") from error
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or f"gh exited with code {result.returncode}"
        raise RuntimeError(f"{failure_message}\n{detail}")
    return result.stdout.strip()


def ensure_github_authentication() -> None:
    run_gh(
        args=["auth", "status", "--active", "--hostname", GITHUB_HOST],
        failure_message="GitHub CLI is not logged in to github.com. Run `gh auth login --hostname github.com` and retry.",
    )


def require_json_object(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise RuntimeError(f"Expected {context} to be a JSON object.")
    return cast(dict[str, object], value)


def load_installer_data(path: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    payload_value: object = json.loads(path.read_text(encoding="utf-8"))
    payload = require_json_object(value=payload_value, context=str(path))
    installers_value = payload.get("installers")
    if not isinstance(installers_value, list):
        raise RuntimeError(f"Expected {path} to contain an 'installers' array.")
    installers = [
        require_json_object(value=installer, context=f"installers[{index}]")
        for index, installer in enumerate(installers_value)
    ]
    return payload, installers


def github_repository(repo_url: str) -> str | None:
    parsed_url = urlsplit(repo_url)
    if parsed_url.hostname not in {GITHUB_HOST, f"www.{GITHUB_HOST}"}:
        return None
    path_parts = [part for part in parsed_url.path.split("/") if part]
    if len(path_parts) != 2:
        raise RuntimeError(f"Expected a GitHub repository URL, received: {repo_url}")
    owner, repo = path_parts
    normalized_repo = repo.removesuffix(".git")
    return f"{owner}/{normalized_repo}"


def fetch_last_commit_date(repository: str) -> str:
    owner, repo = repository.split("/", maxsplit=1)
    endpoint = f"repos/{quote(owner, safe='')}/{quote(repo, safe='')}/commits?per_page=1"
    last_commit_date = run_gh(
        args=["api", "--hostname", GITHUB_HOST, endpoint, "--jq", ".[0].commit.committer.date"],
        failure_message=f"Failed to fetch the latest commit for {repository}.",
    )
    if not last_commit_date:
        raise RuntimeError(f"GitHub returned no commits for {repository}.")
    return last_commit_date


def update_installer_commit_dates(path: Path) -> int:
    ensure_github_authentication()
    payload, installers = load_installer_data(path=path)
    repositories_by_key: dict[str, str] = {}
    repository_keys_by_installer_index: dict[int, str] = {}

    for index, installer in enumerate(installers):
        repo_url = installer.get("repoURL")
        if not isinstance(repo_url, str):
            raise RuntimeError(f"Expected installers[{index}].repoURL to be a string.")
        repository = github_repository(repo_url=repo_url)
        if repository is None:
            continue
        repository_key = repository.casefold()
        repositories_by_key.setdefault(repository_key, repository)
        repository_keys_by_installer_index[index] = repository_key

    commit_dates_by_repository_key: dict[str, str] = {}
    repository_count = len(repositories_by_key)
    for position, (repository_key, repository) in enumerate(repositories_by_key.items(), start=1):
        print(f"[{position}/{repository_count}] {repository}")
        commit_dates_by_repository_key[repository_key] = fetch_last_commit_date(repository=repository)

    checked_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    for index, installer in enumerate(installers):
        repository_key = repository_keys_by_installer_index.get(index)
        updated_installer = {
            key: value
            for key, value in installer.items()
            if key not in {"lastCommitDate", "lastCommitDateCheckDate"}
        }
        if repository_key is not None:
            metadata = CommitDateMetadata(
                lastCommitDate=commit_dates_by_repository_key[repository_key],
                lastCommitDateCheckDate=checked_at,
            )
            ordered_installer: dict[str, object] = {}
            for key, value in updated_installer.items():
                ordered_installer[key] = value
                if key == "repoURL":
                    ordered_installer.update(metadata)
            updated_installer = ordered_installer
        installers[index] = updated_installer

    payload["installers"] = installers
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return len(repository_keys_by_installer_index)


def main() -> None:
    try:
        updated_count = update_installer_commit_dates(path=INSTALLER_DATA_PATH)
    except (OSError, json.JSONDecodeError, RuntimeError) as error:
        raise SystemExit(str(error)) from error
    print(f"Updated commit metadata for {updated_count} installers in {INSTALLER_DATA_PATH}.")


if __name__ == "__main__":
    main()
