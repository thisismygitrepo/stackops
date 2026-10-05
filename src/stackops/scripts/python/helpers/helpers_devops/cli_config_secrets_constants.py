from typing import Literal, TypeAlias

CANDIDATE_DISPLAY_LIMIT = 10

SECRETS_SCHEMA_FILENAME = "secrets.schema.json"
SecretsSource: TypeAlias = Literal["local", "l", "global", "g", "both", "b"]
WritableSecretsSource: TypeAlias = Literal["local", "l", "global", "g"]
