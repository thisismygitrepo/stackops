from typing import NotRequired, TypeAlias, TypedDict


SecretScope: TypeAlias = str
SecretScopes: TypeAlias = list[SecretScope]
SecretStringMap: TypeAlias = dict[str, str]
SecretValueMap: TypeAlias = dict[str, object]


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


class Login(TypedDict):
    name: str
    secrets: list[SecretRecord]
    tags: NotRequired[list[str]]
    description: NotRequired[str]
    url: NotRequired[str]
    email: NotRequired[str]
    username: NotRequired[str]
    accountName: NotRequired[str]
    metadata: NotRequired[SecretStringMap]


SecretsFile = TypedDict(
    "SecretsFile",
    {
        "$schema": NotRequired[str],
        "version": str,
        "entries": list[Login],
    },
)
