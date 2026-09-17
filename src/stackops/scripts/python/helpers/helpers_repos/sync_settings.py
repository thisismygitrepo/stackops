from typing import cast

from stackops.utils.schemas.repos.repos_types import RepoSync


def validate_repo_sync(value: object) -> RepoSync:
    if not isinstance(value, dict):
        raise ValueError("Repository sync must be an object")
    data = cast(dict[str, object], value)
    mode = data.get("mode")
    if mode == "git":
        if set(data) != {"mode"}:
            raise ValueError("Git repository sync must contain only mode")
        return {"mode": "git"}
    if mode != "guard":
        raise ValueError("Repository sync mode must be 'git' or 'guard'")
    if set(data) != {"mode", "cloud", "remotePath", "ignoreGitignore"}:
        raise ValueError("Guard repository sync requires mode, cloud, remotePath, and ignoreGitignore")
    cloud = data["cloud"]
    remote_path = data["remotePath"]
    ignore_gitignore = data["ignoreGitignore"]
    if not isinstance(cloud, str) or not cloud.strip():
        raise ValueError("Guard repository cloud must be a non-empty string")
    if not isinstance(remote_path, str) or not remote_path.strip():
        raise ValueError("Guard repository remotePath must be a non-empty string")
    if not isinstance(ignore_gitignore, bool):
        raise ValueError("Guard repository ignoreGitignore must be a boolean")
    return {"mode": "guard", "cloud": cloud, "remotePath": remote_path, "ignoreGitignore": ignore_gitignore}
