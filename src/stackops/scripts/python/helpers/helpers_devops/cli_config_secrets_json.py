import json
from pathlib import Path

from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_candidates import SecretCandidate
from stackops.secrets.models import Login, SecretsFile


def render_secret_search_json(candidates: tuple[SecretCandidate, ...]) -> str:
    source_file = candidates[0].secrets_file
    entries: list[Login] = []
    selected_entry_locations: set[tuple[Path | None, int]] = set()
    for candidate in candidates:
        entry_location = (candidate.source_path, candidate.entry_index)
        if entry_location in selected_entry_locations:
            continue
        selected_entry_locations.add(entry_location)
        entries.append(candidate.login_entry)

    payload: SecretsFile = {"version": source_file["version"], "entries": entries}
    if "$schema" in source_file:
        payload["$schema"] = source_file["$schema"]
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
