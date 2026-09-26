import json
import os
from pathlib import Path
from typing import cast
from urllib.parse import urlsplit

from stackops.scripts.python.ai.initai_artifacts import write_text_artifact
from stackops.scripts.python.ai.initai_models import ArtifactChange
from stackops.scripts.python.ai.utils import generic
from stackops.scripts.python.ai.utils.shared import get_generic_instructions_path

SETTINGS_SCHEMA_URL = "https://json.schemastore.org/claude-code-settings.json"


def _write_json_if_missing(*, repo_root: Path, path: Path, content: dict[str, object]) -> ArtifactChange | None:
    return write_text_artifact(
        repo_root=repo_root,
        path=path,
        content=json.dumps(content, indent=2) + "\n",
        write_mode="if_missing",
    )


def _shared_project_settings() -> dict[str, object]:
    return {
        "$schema": SETTINGS_SCHEMA_URL,
        "respectGitignore": True,
        "permissions": {
            "deny": [
                "Read(./.env)",
                "Read(./.env.*)",
                "Read(./secrets/**)",
                "Read(./config/credentials.json)",
                "Bash(curl *)",
                "Bash(wget *)",
            ]
        },
        "enableAllProjectMcpServers": False,
    }


def _private_local_settings() -> dict[str, object]:
    return {
        "$schema": SETTINGS_SCHEMA_URL,
        "env": {
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
            "CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY": "1",
            "DISABLE_TELEMETRY": "1",
            "DISABLE_ERROR_REPORTING": "1",
            "DISABLE_BUG_COMMAND": "1",
        },
    }


def _enforce_openrouter_zdr(repo_root: Path) -> ArtifactChange | None:
    local_path = repo_root.joinpath(".claude/settings.local.json")
    shared_path = repo_root.joinpath(".claude/settings.json")
    shared_settings = cast(dict[str, object], json.loads(shared_path.read_text(encoding="utf-8")))
    local_settings = cast(dict[str, object], json.loads(local_path.read_text(encoding="utf-8")))
    shared_env = cast(dict[str, str], shared_settings.get("env", {}))
    local_env = cast(dict[str, str], local_settings.get("env", {}))
    effective_env = {**shared_env, **local_env}
    base_url = os.path.expandvars(effective_env.get("ANTHROPIC_BASE_URL", ""))
    host = urlsplit(base_url).hostname or ""
    if host != "openrouter.ai" and not host.endswith(".openrouter.ai"):
        return None
    extra_body = cast(dict[str, object], json.loads(effective_env.get("CLAUDE_CODE_EXTRA_BODY", "{}")))
    provider = cast(dict[str, object], extra_body.setdefault("provider", {}))
    provider["zdr"] = True
    updated_body = json.dumps(extra_body)
    if local_env.get("CLAUDE_CODE_EXTRA_BODY") == updated_body:
        return None
    local_settings["env"] = {**local_env, "CLAUDE_CODE_EXTRA_BODY": updated_body}
    return write_text_artifact(
        repo_root=repo_root,
        path=local_path,
        content=json.dumps(local_settings, indent=2) + "\n",
        write_mode="always",
    )


def build_configuration(repo_root: Path, add_private_config: bool, add_instructions: bool) -> tuple[ArtifactChange, ...]:
    changes: list[ArtifactChange] = []
    if add_instructions:
        instructions_path = get_generic_instructions_path()
        change = write_text_artifact(
            repo_root=repo_root,
            path=repo_root.joinpath("CLAUDE.md"),
            content=instructions_path.read_text(encoding="utf-8"),
            write_mode="always",
        )
        assert change is not None
        changes.append(change)

    if add_private_config:
        shared_settings_change = _write_json_if_missing(
            repo_root=repo_root,
            path=repo_root.joinpath(".claude/settings.json"),
            content=_shared_project_settings(),
        )
        local_settings_change = _write_json_if_missing(
            repo_root=repo_root,
            path=repo_root.joinpath(".claude/settings.local.json"),
            content=_private_local_settings(),
        )
        mcp_change = _write_json_if_missing(
            repo_root=repo_root,
            path=repo_root.joinpath(".mcp.json"),
            content={"mcpServers": {}},
        )
        changes.extend(
            change
            for change in (shared_settings_change, local_settings_change, mcp_change)
            if change is not None
        )
        zdr_change = _enforce_openrouter_zdr(repo_root)
        if zdr_change is not None:
            changes.append(zdr_change)

        claude_local_path = repo_root.joinpath("CLAUDE.local.md")
        local_instructions_change = write_text_artifact(
            repo_root=repo_root,
            path=claude_local_path,
            content=(
                "# Local Claude Code preferences\n\n"
                "- Keep credentials in environment variables, never in tracked files.\n"
                "- Store personal workflow notes here; do not commit sensitive context.\n"
                "- Use `.mcp.json` for shared MCP servers and keep secrets in local environment variables.\n"
            ),
            write_mode="if_missing",
        )
        if local_instructions_change is not None:
            changes.append(local_instructions_change)

        dot_git_ignore_path = repo_root.joinpath(".gitignore")
        gitignore_change = write_text_artifact(
            repo_root=repo_root,
            path=dot_git_ignore_path,
            content="",
            write_mode="if_missing",
        )
        gitignore_written = generic.adjust_gitignore(
            repo_root=repo_root,
            include_default_entries=False,
            extra_entries=[".claude/settings.local.json", "CLAUDE.local.md"],
        )
        if gitignore_change is not None:
            changes.append(gitignore_change)
        elif gitignore_written:
            changes.append(ArtifactChange(path=Path(".gitignore"), action="written"))
    return tuple(changes)
