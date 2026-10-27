from typing import Literal, TypeAlias

CANDIDATE_DISPLAY_LIMIT = 10

SecretsSource: TypeAlias = Literal["project", "p", "user", "u", "all", "a"]
WritableSecretsSource: TypeAlias = Literal["project", "p", "user", "u"]
