from typing import NotRequired, TypeAlias, TypedDict


SecretScope: TypeAlias = str
SecretScopes: TypeAlias = list[SecretScope]
SecretStringMap: TypeAlias = dict[str, str]
SecretJsonValue: TypeAlias = str | int | float | bool | None | list["SecretJsonValue"] | dict[str, "SecretJsonValue"]
SecretValueMap: TypeAlias = dict[str, SecretJsonValue]


class SecretRotation(TypedDict, total=False):
    lastRotated: str
    rotateEveryDays: int
    owner: str


class SecretRecord(TypedDict):
    tags: list[str]
    scopes: SecretScopes
    keyValues: SecretValueMap
    name: NotRequired[str]
    description: NotRequired[str]
    rotation: NotRequired[SecretRotation]
    metadata: NotRequired[SecretStringMap]
    notes: NotRequired[str]


class SecretsEntry(TypedDict):
    name: str
    secrets: list[SecretRecord]
    tags: NotRequired[list[str]]
    description: NotRequired[str]
    url: NotRequired[str]
    email: NotRequired[str]
    username: NotRequired[str]
    profile: NotRequired[str]
    metadata: NotRequired[SecretStringMap]


SecretsFile = TypedDict(
    "SecretsFile",
    {
        "$schema": NotRequired[str],
        "version": str,
        "entries": list[SecretsEntry],
    },
)
