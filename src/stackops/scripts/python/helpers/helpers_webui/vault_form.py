from dataclasses import dataclass
from typing import cast

from stackops.secrets.models import Login


@dataclass(frozen=True)
class VaultProblem:
    status: int
    message: str


# The Vault page sends a login as the file holds it, except that each secret carries `values`, its rows in order, in place of `keyValues`.
# A row whose value was left alone carries `kept`, the secret and key that value has in the login being replaced, instead of the value itself:
# a value nobody asked to see is never sent to the browser, so it cannot come back from there. What this returns still has to pass the loader.
def login_from_form(form: object, original: Login | None) -> dict[str, object] | VaultProblem:
    fields = cast(dict[str, object], form) if isinstance(form, dict) else {}
    secrets_raw = fields.get("secrets")
    if not isinstance(secrets_raw, list):
        return VaultProblem(status=400, message="`login` must be an object with a list of `secrets`.")
    secrets: list[dict[str, object]] = []
    for secret_raw in cast(list[object], secrets_raw):
        secret = cast(dict[str, object], secret_raw) if isinstance(secret_raw, dict) else {}
        key_values = _key_values(rows=secret.get("values"), original=original)
        match key_values:
            case VaultProblem():
                return key_values
            case dict():
                secrets.append({**{field: content for field, content in secret.items() if field != "values"}, "keyValues": key_values})
    return {**fields, "secrets": secrets}


def _key_values(rows: object, original: Login | None) -> dict[str, object] | VaultProblem:
    if not isinstance(rows, list):
        return VaultProblem(status=400, message="Each secret must carry its `values` as a list of rows.")
    key_values: dict[str, object] = {}
    for row_raw in cast(list[object], rows):
        row = cast(dict[str, object], row_raw) if isinstance(row_raw, dict) else {}
        key = row.get("key")
        if not isinstance(key, str) or key.strip() == "":
            return VaultProblem(status=422, message="Every value needs a name.")
        if key in key_values:
            return VaultProblem(status=422, message=f"""The name {key} is used twice in one secret.""")
        match row.get("kept"):
            case None if "value" in row:
                key_values[key] = row["value"]
            case [int() as secret_index, str() as kept_key] if (
                original is not None and 0 <= secret_index < len(original["secrets"]) and kept_key in original["secrets"][secret_index]["keyValues"]
            ):
                key_values[key] = original["secrets"][secret_index]["keyValues"][kept_key]
            case _:
                return VaultProblem(status=400, message=f"""The value of {key} was neither given nor found in the login being changed.""")
    return key_values
