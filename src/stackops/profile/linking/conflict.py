from typing import Literal, TypeAlias

ON_CONFLICT_LOOSE: TypeAlias = Literal[
    "throw-error",
    "t",
    "overwrite-self-managed",
    "os",
    "backup-self-managed",
    "bs",
    "overwrite-default-path",
    "od",
    "backup-default-path",
    "bd",
]
ON_CONFLICT_STRICT: TypeAlias = Literal[
    "throw-error",
    "overwrite-self-managed",
    "backup-self-managed",
    "overwrite-default-path",
    "backup-default-path",
]
ON_CONFLICT_MAPPER: dict[ON_CONFLICT_LOOSE, ON_CONFLICT_STRICT] = {
    "t": "throw-error",
    "os": "overwrite-self-managed",
    "bs": "backup-self-managed",
    "od": "overwrite-default-path",
    "bd": "backup-default-path",
    "throw-error": "throw-error",
    "overwrite-self-managed": "overwrite-self-managed",
    "backup-self-managed": "backup-self-managed",
    "overwrite-default-path": "overwrite-default-path",
    "backup-default-path": "backup-default-path",
}
