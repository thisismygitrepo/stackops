import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, NoReturn, cast

import typer

__all__ = ["SecretCandidate", "SecretSelectors", "load_secret_candidates", "resolve_candidate"]


@dataclass(frozen=True)
class SecretCandidate:
    json_path: str
    entry_name: str
    entry_tags: tuple[str, ...]
    secret_name: str | None
    secret_tags: tuple[str, ...]
    scopes: tuple[str, ...]
    key_values: dict[str, str]
    searchable_values: tuple[str, ...]


@dataclass(frozen=True)
class SecretSelectors:
    entry_name: str | None = None
    secret_name: str | None = None
    tags: tuple[str, ...] = ()
    entry_tags: tuple[str, ...] = ()
    secret_tags: tuple[str, ...] = ()
    scopes: tuple[str, ...] = ()
    keys: tuple[str, ...] = ()

    def has_any(self) -> bool:
        return any(
            (
                self.entry_name is not None,
                self.secret_name is not None,
                bool(self.tags),
                bool(self.entry_tags),
                bool(self.secret_tags),
                bool(self.scopes),
                bool(self.keys),
            )
        )


def load_secret_candidates(secrets_path: Path) -> list[SecretCandidate]:
    if not secrets_path.exists():
        _fail(f"Secrets file not found: {secrets_path}")

    try:
        payload = json.loads(secrets_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        _fail(f"Invalid JSON in {secrets_path}: {exc.msg} at line {exc.lineno}, column {exc.colno}.")

    if not isinstance(payload, Mapping):
        _fail(f"Secrets file must contain a JSON object: {secrets_path}")

    entries = payload.get("entries")
    if not isinstance(entries, list):
        _fail(f"Secrets file must define an entries array: {secrets_path}")
    entries_list = cast(list[Any], entries)

    candidates: list[SecretCandidate] = []
    for entry_index, entry_raw in enumerate(entries_list):
        if not isinstance(entry_raw, Mapping):
            _fail(f"Invalid secrets entry at entries[{entry_index}]: expected object.")
        candidates.extend(_entry_candidates(entry=entry_raw, entry_index=entry_index))

    if not candidates:
        _fail(f"No keyValues entries found in {secrets_path}")
    return candidates


def _entry_candidates(entry: Mapping[str, Any], entry_index: int) -> list[SecretCandidate]:
    entry_name = _string_value(entry.get("name"), f"entries[{entry_index}].name")
    entry_tags = _string_tuple(entry.get("tags"), f"entries[{entry_index}].tags")
    secrets_raw = entry.get("secrets")
    if not isinstance(secrets_raw, list):
        _fail(f"Invalid secrets entry at entries[{entry_index}].secrets: expected array.")
    secrets = cast(list[Any], secrets_raw)

    shared_search_values = _search_values_from_entry(entry=entry, entry_name=entry_name, entry_tags=entry_tags)

    candidates: list[SecretCandidate] = []
    for secret_index, secret_raw in enumerate(secrets):
        if not isinstance(secret_raw, Mapping):
            _fail(f"Invalid secret at entries[{entry_index}].secrets[{secret_index}]: expected object.")

        key_values_path = f"entries[{entry_index}].secrets[{secret_index}].keyValues"
        key_values = _key_values(secret_raw.get("keyValues"), key_values_path)
        secret_name = _optional_string(secret_raw.get("name"), f"entries[{entry_index}].secrets[{secret_index}].name")
        secret_tags = _string_tuple(secret_raw.get("tags"), f"entries[{entry_index}].secrets[{secret_index}].tags")
        scopes = _scope_tuple(secret_raw.get("scope"), f"entries[{entry_index}].secrets[{secret_index}].scope")
        secret_search_values = _search_values_from_secret(
            secret=secret_raw, secret_name=secret_name, secret_tags=secret_tags, scopes=scopes, key_names=tuple(key_values)
        )
        candidates.append(
            SecretCandidate(
                json_path=key_values_path,
                entry_name=entry_name,
                entry_tags=entry_tags,
                secret_name=secret_name,
                secret_tags=secret_tags,
                scopes=scopes,
                key_values=key_values,
                searchable_values=shared_search_values + secret_search_values,
            )
        )
    return candidates


def _search_values_from_entry(entry: Mapping[str, Any], entry_name: str, entry_tags: tuple[str, ...]) -> tuple[str, ...]:
    values: list[str] = [entry_name, *entry_tags]
    for key in ("description", "url", "email", "username", "profile"):
        value = entry.get(key)
        if isinstance(value, str):
            values.append(value)
    values.extend(_string_map_terms(entry.get("metadata")))
    return tuple(values)


def _search_values_from_secret(
    secret: Mapping[str, Any], secret_name: str | None, secret_tags: tuple[str, ...], scopes: tuple[str, ...], key_names: tuple[str, ...]
) -> tuple[str, ...]:
    values: list[str] = [*secret_tags, *scopes, *key_names]
    if secret_name is not None:
        values.append(secret_name)
    for key in ("description", "notes"):
        value = secret.get(key)
        if isinstance(value, str):
            values.append(value)
    values.extend(_string_map_terms(secret.get("metadata")))
    return tuple(values)


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


def _candidate_matches(candidate: SecretCandidate, terms: tuple[str, ...]) -> bool:
    searchable_values = tuple(value.casefold() for value in candidate.searchable_values)
    return all(any(term in searchable_value for searchable_value in searchable_values) for term in terms)


def _candidate_matches_selectors(candidate: SecretCandidate, selectors: SecretSelectors) -> bool:
    if selectors.entry_name is not None and candidate.entry_name != selectors.entry_name:
        return False
    if selectors.secret_name is not None and candidate.secret_name != selectors.secret_name:
        return False
    if not all(tag in candidate.entry_tags or tag in candidate.secret_tags for tag in selectors.tags):
        return False
    if not all(tag in candidate.entry_tags for tag in selectors.entry_tags):
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
    lines = [
        f"# {_candidate_label(candidate)}",
        "",
        f"- Path: `{candidate.json_path}`",
        f"- Entry: `{candidate.entry_name}`",
        f"- Entry tags: `{_preview_join(candidate.entry_tags)}`",
    ]
    if candidate.secret_name is not None:
        lines.append(f"- Secret name: `{candidate.secret_name}`")
    lines.extend(
        (
            f"- Secret tags: `{_preview_join(candidate.secret_tags)}`",
            f"- Scope: `{_preview_join(candidate.scopes)}`",
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
    if selectors.entry_name is not None:
        parts.append(f"name={selectors.entry_name}")
    if selectors.secret_name is not None:
        parts.append(f"secret-name={selectors.secret_name}")
    parts.extend(f"tag={tag}" for tag in selectors.tags)
    parts.extend(f"entry-tag={tag}" for tag in selectors.entry_tags)
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
    keys = ", ".join(candidate.key_values)
    return f"{candidate.entry_name} / {secret_label} -> {keys}"


def _string_value(value: Any, path: str) -> str:
    if isinstance(value, str) and value.strip():
        return value
    _fail(f"Invalid secrets file: {path} must be a non-empty string.")


def _optional_string(value: Any, path: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, str) and value.strip():
        return value
    _fail(f"Invalid secrets file: {path} must be a non-empty string when present.")


def _string_tuple(value: Any, path: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        _fail(f"Invalid secrets file: {path} must be an array of strings when present.")
    values: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            _fail(f"Invalid secrets file: {path}[{index}] must be a non-empty string.")
        values.append(item)
    return tuple(values)


def _scope_tuple(value: Any, path: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str) and value.strip():
        return (value,)
    return _string_tuple(value, path)


def _key_values(value: Any, path: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        _fail(f"Invalid secrets file: {path} must be an object.")

    key_values: dict[str, str] = {}
    for key, secret_value in value.items():
        if not isinstance(key, str) or not key.strip():
            _fail(f"Invalid secrets file: {path} contains a non-string or empty key.")
        if not isinstance(secret_value, str):
            _fail(f"Invalid secrets file: {path}.{key} must be a string.")
        key_values[key] = secret_value
    if not key_values:
        _fail(f"Invalid secrets file: {path} must define at least one value.")
    return key_values


def _string_map_terms(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Mapping):
        return ()
    terms: list[str] = []
    for key, item in value.items():
        if isinstance(key, str):
            terms.append(key)
        if isinstance(item, str):
            terms.append(item)
    return tuple(terms)


def _fail(message: str) -> NoReturn:
    typer.echo(typer.style("Error: ", fg=typer.colors.RED) + message)
    raise typer.Exit(code=1)
