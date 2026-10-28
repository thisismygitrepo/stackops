from typing import Literal, TypeAlias

CANDIDATE_DISPLAY_LIMIT = 10

SecretsSource: TypeAlias = Literal["workspace", "w", "user", "u", "all", "a"]
WritableSecretsSource: TypeAlias = Literal["workspace", "w", "user", "u"]
