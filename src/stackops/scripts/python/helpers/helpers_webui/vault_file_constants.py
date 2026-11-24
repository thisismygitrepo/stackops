from typing import Final, Literal

# A secret whose next replacement is this close counts as due soon.
VAULT_DUE_SOON_DAYS: Final[int] = 14

type VaultSchemaState = Literal["current", "stale", "missing"]
type VaultRotationState = Literal["due", "soon", "fine", "undated", "unscheduled"]
# What stands at the place a copy is to be written to: nothing, a vault file, a file of some other kind, a folder, the file being copied from,
# or a folder that does not exist yet.
type VaultCopyTargetState = Literal["free", "vault", "other", "folder", "same", "nowhere"]
type VaultCopyConflict = Literal["throw-error", "overwrite", "append"]

# A field of the vault file as a person would call it, by the name the file gives it.
VAULT_FIELD_WORDS: Final[dict[str, str]] = {
    "name": "its name",
    "tags": "its tags",
    "scopes": "its scopes",
    "keyValues": "its values",
    "secrets": "its secrets",
    "description": "its description",
    "url": "its web address",
    "email": "its email",
    "username": "its user name",
    "accountName": "its account name",
    "metadata": "its other details",
    "rotation": "its rotation record",
    "lastRotated": "the date it was last replaced",
    "rotateEveryDays": "how often it is replaced",
    "owner": "who replaces it",
    "version": "the file's version",
    "entries": "the list of logins",
}
# What the full check's rules mean, by the name the schema gives each rule. `{place}` is the field or thing the check points at.
VAULT_SCHEMA_RULE_WORDS: Final[dict[str, str]] = {
    "required": "A field that must be there is missing from {place}.",
    "additionalProperties": "There is a field the vault does not know in {place}.",
    "type": "The wrong kind of thing is in {place}, such as text where a list belongs.",
    "minItems": "At least one item is needed in {place}, and it is empty.",
    "minLength": "Some text is needed in {place}, and it is empty.",
    "pattern": "What is written in {place} is empty, or in a form the vault does not accept.",
    "uniqueItems": "The same thing is listed twice in {place}.",
    "minimum": "The number in {place} is too small.",
    "format": "What is written in {place} is not in the form its kind asks for, such as a date.",
}
