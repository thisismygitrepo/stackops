from typing import Literal, cast

EncryptionMode = Literal["symmetric", "asymmetric"]
ENCRYPTION_MODES: tuple[EncryptionMode, ...] = ("symmetric", "asymmetric")
ENCRYPTION_MODES_DISPLAY = "symmetric, asymmetric"


def parse_encryption_mode(value: object, *, label: str = "encryption") -> EncryptionMode:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be one of: {ENCRYPTION_MODES_DISPLAY}.")
    token = value.strip().lower()
    if token in ENCRYPTION_MODES:
        return cast(EncryptionMode, token)
    raise ValueError(f"{label} must be one of: {ENCRYPTION_MODES_DISPLAY}.")
