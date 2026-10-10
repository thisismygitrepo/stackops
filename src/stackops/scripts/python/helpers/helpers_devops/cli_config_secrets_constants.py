from typing import Literal, TypeAlias

CANDIDATE_DISPLAY_LIMIT = 10

SecretsSource: TypeAlias = Literal["local", "l", "global", "g", "both", "b"]
WritableSecretsSource: TypeAlias = Literal["local", "l", "global", "g"]
