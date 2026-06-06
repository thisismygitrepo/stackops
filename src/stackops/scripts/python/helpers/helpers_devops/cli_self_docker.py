import os
import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, NoReturn

from stackops.secrets import Login, SecretsFileError, render_secret_value, search_logins

DOCKER_DEFAULT_LOGIN_NAME = "docker"
DOCKER_TOKEN_KEY_CANDIDATES = ("DOCKER_TOKEN", "DOCKERHUB_TOKEN", "DOCKER_PASSWORD", "DOCKER_PAT")
ENV_VAR_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class DockerCredentialError(ValueError):
    """Raised when Docker credential selection or env handoff preparation fails."""


@dataclass(frozen=True)
class DockerCredentials:
    login_name: str
    secret_name: str
    username: str
    token_env_key: str
    key_values: Mapping[str, object]


def fresh_op_program_path() -> Path:
    op_program_path_raw = os.environ.get("OP_PROGRAM_PATH")
    if op_program_path_raw is None:
        _fail("Run this command through the StackOps shell wrapper, for example `d self build-docker ai`.")

    op_program_path = Path(op_program_path_raw)
    if op_program_path.exists():
        _fail(f"Cannot prepare Docker credentials because OP_PROGRAM_PATH already exists: {op_program_path}")
    return op_program_path


def resolve_docker_credentials(
    *,
    secrets_path: Path | None,
    login_name: str | None,
    account_name: str | None,
    secret_name: str | None,
    secret_tags: list[str] | None,
    scopes: list[str] | None,
    token_key: str | None,
) -> DockerCredentials:
    clean_login_name = _clean_optional_selector(login_name) or DOCKER_DEFAULT_LOGIN_NAME
    clean_account_name = _clean_optional_selector(account_name)
    clean_secret_name = _clean_optional_selector(secret_name)
    clean_secret_tags = _clean_selector_values(secret_tags)
    clean_scopes = _clean_selector_values(scopes)
    clean_token_key = _clean_optional_selector(token_key)

    token_keys = (clean_token_key,) if clean_token_key is not None else DOCKER_TOKEN_KEY_CANDIDATES
    matches: list[DockerCredentials] = []
    for candidate_token_key in token_keys:
        try:
            logins = search_logins(
                path=secrets_path,
                login_name=clean_login_name,
                account_name=clean_account_name,
                secret_name=clean_secret_name,
                secret_tags=clean_secret_tags,
                scopes=clean_scopes,
                keys=(candidate_token_key,),
            )
        except SecretsFileError as exc:
            _fail(f"Docker credential search failed: {exc}")
        matches.extend(_docker_credentials_from_login(login=login, token_env_key=candidate_token_key) for login in logins)

    matches = _unique_docker_credentials(matches)
    if len(matches) == 1:
        return matches[0]

    selection = _format_docker_credential_selection(
        login_name=clean_login_name,
        account_name=clean_account_name,
        secret_name=clean_secret_name,
        secret_tags=clean_secret_tags,
        scopes=clean_scopes,
        token_keys=token_keys,
        secrets_path=secrets_path,
    )
    if not matches:
        _fail(
            "No Docker credential bundle matched StackOps secrets selectors: "
            + selection
            + "\nExpected one login with entries[].username set to the Docker image namespace and keyValues containing a token env var."
        )

    match_lines = "\n".join(f"  - {_docker_credentials_label(match)}" for match in matches)
    _fail(
        "Docker credential selectors matched more than one bundle: "
        + selection
        + "\nMatching bundles:\n"
        + match_lines
        + "\nNarrow the match with --docker-login-name, --docker-secret-name, --docker-secret-tag, --docker-scope, or --docker-token-key."
    )


def validate_env_names(key_values: Mapping[str, object]) -> None:
    invalid_names = [name for name in key_values if ENV_VAR_NAME_RE.fullmatch(name) is None]
    if invalid_names:
        _fail(f"Invalid Docker credential environment variable name(s): {', '.join(invalid_names)}")


def docker_secret_env_path(op_program_path: Path) -> Path:
    return op_program_path.with_name(f"{op_program_path.stem}.docker.secrets.env.sh")


def write_private_docker_env_file(secret_env_path: Path, key_values: Mapping[str, object]) -> None:
    if secret_env_path.exists():
        _fail(f"Cannot write Docker secrets env file because it already exists: {secret_env_path}")

    secret_env_path.parent.mkdir(parents=True, exist_ok=True)
    secret_env_path.write_text(_render_private_docker_env_file(key_values), encoding="utf-8")
    secret_env_path.chmod(0o600)


def render_build_docker_shell_script(
    *,
    variant: str,
    repo_root: Path,
    script_path: Path,
    secret_env_path: Path,
    docker_username: str,
    token_env_key: str,
    credential_env_keys: tuple[str, ...],
) -> str:
    unset_credential_keys = " ".join(shlex.quote(key) for key in credential_env_keys)
    lines = [
        "set +x",
        f"_stackops_docker_secret_env_file={shlex.quote(str(secret_env_path))}",
        "_stackops_docker_cleanup() {",
        '  rm -f "$_stackops_docker_secret_env_file"',
        "  unset DOCKER_IMAGE_NAMESPACE DOCKER_LOGIN_TOKEN_ENV_VAR",
    ]
    if unset_credential_keys:
        lines.append(f"  unset {unset_credential_keys}")
    lines.extend(
        [
            "}",
            'if [ ! -f "$_stackops_docker_secret_env_file" ]; then',
            '  echo "StackOps Docker secrets env file is missing: $_stackops_docker_secret_env_file" >&2',
            "  _stackops_docker_cleanup",
            "  return 1 2>/dev/null || exit 1",
            "fi",
            '. "$_stackops_docker_secret_env_file"',
            'rm -f "$_stackops_docker_secret_env_file"',
            f"export DOCKER_IMAGE_NAMESPACE={shlex.quote(docker_username)}",
            f"export DOCKER_LOGIN_TOKEN_ENV_VAR={shlex.quote(token_env_key)}",
            f"export VARIANT={shlex.quote(variant)}",
            f"cd {shlex.quote(str(repo_root))}",
            f"bash {shlex.quote(str(script_path))}",
            "_stackops_docker_exit_code=$?",
            "_stackops_docker_cleanup",
            "unset -f _stackops_docker_cleanup 2>/dev/null || true",
            'return "$_stackops_docker_exit_code" 2>/dev/null || exit "$_stackops_docker_exit_code"',
        ]
    )
    return "\n".join(lines) + "\n"


def _docker_credentials_from_login(*, login: Login, token_env_key: str) -> DockerCredentials:
    secret = login["secrets"][0]
    username = login.get("username")
    if not isinstance(username, str) or not username.strip():
        _fail(f"Matched Docker credential login '{login['name']}' must define entries[].username for the Docker image namespace.")

    key_values = dict(secret["keyValues"])
    if token_env_key not in key_values:
        _fail(f"Matched Docker credential secret '{secret['name']}' does not contain token env var '{token_env_key}'.")

    return DockerCredentials(
        login_name=login["name"],
        secret_name=secret["name"],
        username=username.strip(),
        token_env_key=token_env_key,
        key_values=key_values,
    )


def _unique_docker_credentials(matches: list[DockerCredentials]) -> list[DockerCredentials]:
    unique_matches: list[DockerCredentials] = []
    seen: set[tuple[str, str, str]] = set()
    for match in matches:
        identity = (match.login_name, match.secret_name, match.username)
        if identity in seen:
            continue
        seen.add(identity)
        unique_matches.append(match)
    return unique_matches


def _format_docker_credential_selection(
    *,
    login_name: str | None,
    account_name: str | None,
    secret_name: str | None,
    secret_tags: tuple[str, ...],
    scopes: tuple[str, ...],
    token_keys: tuple[str, ...],
    secrets_path: Path | None,
) -> str:
    parts: list[str] = []
    if secrets_path is not None:
        parts.append(f"path={secrets_path}")
    if login_name is not None:
        parts.append(f"login-name={login_name}")
    if account_name is not None:
        parts.append(f"account-name={account_name}")
    if secret_name is not None:
        parts.append(f"secret-name={secret_name}")
    parts.extend(f"secret-tag={tag}" for tag in secret_tags)
    parts.extend(f"scope={scope}" for scope in scopes)
    parts.append(f"token-key={'|'.join(token_keys)}")
    return ", ".join(parts)


def _docker_credentials_label(credentials: DockerCredentials) -> str:
    keys = ", ".join(credentials.key_values) if credentials.key_values else "<no env vars>"
    return (
        f"{credentials.login_name} / {credentials.secret_name} "
        f"-> username={credentials.username}, token-env={credentials.token_env_key}, env-vars={keys}"
    )


def _render_private_docker_env_file(key_values: Mapping[str, object]) -> str:
    lines = ["# StackOps Docker secrets env file. This file is removed after loading.", "set +x"]
    for key, value in key_values.items():
        lines.append(f"export {key}={shlex.quote(render_secret_value(value))}")
    return "\n".join(lines) + "\n"


def _clean_optional_selector(value: str | None) -> str | None:
    if value is None:
        return None
    stripped_value = value.strip()
    return stripped_value or None


def _clean_selector_values(values: list[str] | None) -> tuple[str, ...]:
    return tuple(stripped_value for value in values or () if (stripped_value := value.strip()))


def _fail(message: str) -> NoReturn:
    raise DockerCredentialError(message)
