from dataclasses import dataclass, replace
from pathlib import Path
from typing import NoReturn

import typer

from stackops.utils.schemas.secrets.secrets_loader import SecretsSchemaError, load_secrets_file
from stackops.utils.schemas.secrets.secrets_types import Login, SecretRecord, SecretStringMap, SecretsFile, SecretValueMap

__all__ = [
    "SecretCandidate",
    "SecretSelectors",
    "build_secret_candidates",
    "filter_secret_candidates",
    "format_secret_candidate_label",
    "format_secret_selection",
    "load_secret_candidates",
    "load_secrets_file",
    "resolve_candidate",
]


@dataclass(frozen=True)
class SecretCandidate:
    json_path: str
    login_name: str
    login_tags: tuple[str, ...]
    secret_name: str | None
    secret_tags: tuple[str, ...]
    scopes: tuple[str, ...]
    key_values: SecretValueMap
    searchable_values: tuple[str, ...]
    source_name: str | None = None
    source_path: Path | None = None


@dataclass(frozen=True)
class SecretSelectors:
    login_name: str | None = None
    secret_name: str | None = None
    tags: tuple[str, ...] = ()
    login_tags: tuple[str, ...] = ()
    secret_tags: tuple[str, ...] = ()
    scopes: tuple[str, ...] = ()
    keys: tuple[str, ...] = ()

    def has_any(self) -> bool:
        return any(
            (
                self.login_name is not None,
                self.secret_name is not None,
                bool(self.tags),
                bool(self.login_tags),
                bool(self.secret_tags),
                bool(self.scopes),
                bool(self.keys),
            )
        )


def load_secret_candidates(secrets_path: Path, *, source_name: str | None = None) -> list[SecretCandidate]:
    try:
        secrets_file = load_secrets_file(secrets_path)
    except SecretsSchemaError as exc:
        _fail(str(exc))

    candidates = build_secret_candidates(secrets_file)
    if not candidates:
        _fail(f"No keyValues entries found in {secrets_path}")
    return [replace(candidate, source_name=source_name, source_path=secrets_path) for candidate in candidates]


def build_secret_candidates(secrets_file: SecretsFile) -> list[SecretCandidate]:
    candidates: list[SecretCandidate] = []
    for entry_index, entry in enumerate(secrets_file["entries"]):
        candidates.extend(_login_candidates(login=entry, entry_index=entry_index))
    return candidates


def resolve_candidate(candidates: list[SecretCandidate], terms: list[str] | None, selectors: SecretSelectors, interactive: bool) -> SecretCandidate:
    normalized_terms = tuple(term.casefold() for term in terms or () if term.strip())
    if not normalized_terms and not selectors.has_any() and not interactive:
        _fail("Pass at least one term or exact selector to identify a secrets keyValues entry.")

    matches = [
        candidate
        for candidate in candidates
        if _candidate_matches(candidate=candidate, terms=normalized_terms) and _candidate_matches_selectors(candidate=candidate, selectors=selectors)
    ]
    if interactive:
        if not matches:
            selection_text = _selection_text(terms=terms, selectors=selectors)
            typer.echo(typer.style("Error: ", fg=typer.colors.RED) + f"No keyValues entry matched selection: {selection_text}")
            _print_candidate_list("Available keyValues entries:", candidates)
            raise typer.Exit(code=1)
        return _choose_candidate_interactively(matches)

    if len(matches) == 1:
        return matches[0]

    selection_text = _selection_text(terms=terms, selectors=selectors)
    if not matches:
        typer.echo(typer.style("Error: ", fg=typer.colors.RED) + f"No keyValues entry matched selection: {selection_text}")
        _print_candidate_list("Available keyValues entries:", candidates)
    else:
        typer.echo(
            typer.style("Error: ", fg=typer.colors.RED)
            + f"Selection did not identify a unique keyValues entry: {selection_text} matched {len(matches)} entries."
        )
        _print_candidate_list("Matching keyValues entries:", matches)
    raise typer.Exit(code=1)


def filter_secret_candidates(candidates: list[SecretCandidate], selectors: SecretSelectors) -> list[SecretCandidate]:
    return [candidate for candidate in candidates if _candidate_matches_selectors(candidate=candidate, selectors=selectors)]


def format_secret_selection(selectors: SecretSelectors) -> str:
    return _selection_text(terms=None, selectors=selectors)


def format_secret_candidate_label(candidate: SecretCandidate) -> str:
    return _candidate_label(candidate)


def _login_candidates(login: Login, entry_index: int) -> list[SecretCandidate]:
    login_name = login["name"]
    login_tags = tuple(login.get("tags", ()))
    shared_search_values = _search_values_from_login(login=login, login_name=login_name, login_tags=login_tags)

    candidates: list[SecretCandidate] = []
    for secret_index, secret in enumerate(login["secrets"]):
        key_values = dict(secret["keyValues"])
        secret_tags = tuple(secret["tags"])
        scopes = tuple(secret["scopes"])
        secret_name = secret.get("name")
        secret_search_values = _search_values_from_secret(
            secret=secret, secret_name=secret_name, secret_tags=secret_tags, scopes=scopes, key_names=tuple(key_values)
        )
        candidates.append(
            SecretCandidate(
                json_path=f"entries[{entry_index}].secrets[{secret_index}].keyValues",
                login_name=login_name,
                login_tags=login_tags,
                secret_name=secret_name,
                secret_tags=secret_tags,
                scopes=scopes,
                key_values=key_values,
                searchable_values=shared_search_values + secret_search_values,
            )
        )
    return candidates


def _search_values_from_login(login: Login, login_name: str, login_tags: tuple[str, ...]) -> tuple[str, ...]:
    values: list[str] = [login_name, *login_tags]
    for key in ("description", "notes", "url", "email", "username", "profile"):
        value = login.get(key)
        if value is not None:
            values.append(value)
    values.extend(_string_map_terms(login.get("metadata")))
    return tuple(values)


def _search_values_from_secret(
    secret: SecretRecord, secret_name: str | None, secret_tags: tuple[str, ...], scopes: tuple[str, ...], key_names: tuple[str, ...]
) -> tuple[str, ...]:
    values: list[str] = [*secret_tags, *scopes, *key_names]
    if secret_name is not None:
        values.append(secret_name)
    for key in ("description",):
        value = secret.get(key)
        if value is not None:
            values.append(value)
    values.extend(_string_map_terms(secret.get("metadata")))
    return tuple(values)


def _candidate_matches(candidate: SecretCandidate, terms: tuple[str, ...]) -> bool:
    searchable_values = tuple(value.casefold() for value in candidate.searchable_values)
    return all(any(term in searchable_value for searchable_value in searchable_values) for term in terms)


def _candidate_matches_selectors(candidate: SecretCandidate, selectors: SecretSelectors) -> bool:
    if selectors.login_name is not None and candidate.login_name != selectors.login_name:
        return False
    if selectors.secret_name is not None and candidate.secret_name != selectors.secret_name:
        return False
    if not all(tag in candidate.login_tags or tag in candidate.secret_tags for tag in selectors.tags):
        return False
    if not all(tag in candidate.login_tags for tag in selectors.login_tags):
        return False
    if not all(tag in candidate.secret_tags for tag in selectors.secret_tags):
        return False
    if not all(scope in candidate.scopes for scope in selectors.scopes):
        return False
    return all(key in candidate.key_values for key in selectors.keys)


def _choose_candidate_interactively(candidates: list[SecretCandidate]) -> SecretCandidate:
    from stackops.utils.options_utils.tv_options import choose_from_dict_with_preview

    option_to_candidate, option_to_preview = _candidate_picker_options(candidates)
    try:
        selected_label = choose_from_dict_with_preview(
            options_to_preview_mapping=option_to_preview, extension="md", multi=False, preview_size_percent=60.0
        )
    except FileNotFoundError:
        _fail("Interactive selection requires `tv` on PATH.")
    if selected_label is None:
        _fail("Interactive selection cancelled.")

    selected_candidate = option_to_candidate.get(selected_label)
    if selected_candidate is None:
        _fail(f"Interactive selection did not map to a secrets keyValues entry: {selected_label}")
    return selected_candidate


def _candidate_picker_options(candidates: list[SecretCandidate]) -> tuple[dict[str, SecretCandidate], dict[str, str]]:
    base_labels = [_candidate_label(candidate) for candidate in candidates]
    duplicate_labels = {label for label in base_labels if base_labels.count(label) > 1}

    option_to_candidate: dict[str, SecretCandidate] = {}
    option_to_preview: dict[str, str] = {}
    for candidate, base_label in zip(candidates, base_labels, strict=True):
        label = base_label
        if label in duplicate_labels:
            label = f"{base_label} [{candidate.json_path}]"
        option_to_candidate[label] = candidate
        option_to_preview[label] = _candidate_preview(candidate)
    return option_to_candidate, option_to_preview


def _candidate_preview(candidate: SecretCandidate) -> str:
    lines = [f"# {_candidate_label(candidate)}", "", f"- Path: `{candidate.json_path}`"]
    if candidate.source_name is not None:
        lines.append(f"- Source: `{candidate.source_name}`")
    if candidate.source_path is not None:
        lines.append(f"- File: `{candidate.source_path}`")
    lines.extend((f"- Login: `{candidate.login_name}`", f"- Login tags: `{_preview_join(candidate.login_tags)}`"))
    if candidate.secret_name is not None:
        lines.append(f"- Secret name: `{candidate.secret_name}`")
    lines.extend(
        (
            f"- Secret tags: `{_preview_join(candidate.secret_tags)}`",
            f"- Scopes: `{_preview_join(candidate.scopes)}`",
            f"- Env vars: `{_preview_join(tuple(candidate.key_values))}`",
        )
    )
    return "\n".join(lines) + "\n"


def _preview_join(values: tuple[str, ...]) -> str:
    return ", ".join(values) if values else "-"


def _selection_text(terms: list[str] | None, selectors: SecretSelectors) -> str:
    parts: list[str] = []
    terms_text = " ".join(term for term in terms or () if term.strip())
    if terms_text:
        parts.append(f"terms={terms_text}")
    if selectors.login_name is not None:
        parts.append(f"name={selectors.login_name}")
    if selectors.secret_name is not None:
        parts.append(f"secret-name={selectors.secret_name}")
    parts.extend(f"tag={tag}" for tag in selectors.tags)
    parts.extend(f"login-tag={tag}" for tag in selectors.login_tags)
    parts.extend(f"secret-tag={tag}" for tag in selectors.secret_tags)
    parts.extend(f"scope={scope}" for scope in selectors.scopes)
    parts.extend(f"key={key}" for key in selectors.keys)
    return ", ".join(parts) if parts else "<none>"


def _print_candidate_list(title: str, candidates: list[SecretCandidate]) -> None:
    typer.echo(title)
    for candidate in candidates[:10]:
        typer.echo(f"  - {_candidate_label(candidate)}")
    if len(candidates) > 10:
        typer.echo(f"  ... {len(candidates) - 10} more")


def _candidate_label(candidate: SecretCandidate) -> str:
    secret_label = candidate.secret_name
    if secret_label is None and candidate.secret_tags:
        secret_label = ",".join(candidate.secret_tags)
    if secret_label is None:
        secret_label = "<unnamed secret>"
    keys = ", ".join(candidate.key_values) if candidate.key_values else "<no keys>"
    source_prefix = f"[{candidate.source_name}] " if candidate.source_name is not None else ""
    return f"{source_prefix}{candidate.login_name} / {secret_label} -> {keys}"


def _string_map_terms(value: SecretStringMap | None) -> tuple[str, ...]:
    if value is None:
        return ()
    terms: list[str] = []
    for key, item in value.items():
        terms.append(key)
        terms.append(item)
    return tuple(terms)


def _fail(message: str) -> NoReturn:
    typer.echo(typer.style("Error: ", fg=typer.colors.RED) + message)
    raise typer.Exit(code=1)
