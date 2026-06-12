from typing import Literal, TypeAlias

EncryptionMode: TypeAlias = Literal["symmetric", "asymmetric"]
EncryptionModeChoice: TypeAlias = Literal["symmetric", "s", "asymmetric", "a"]
ENCRYPTION_MODES: tuple[EncryptionMode, ...] = ("symmetric", "asymmetric")
ENCRYPTION_MODES_DISPLAY = "symmetric, s, asymmetric, a"


def parse_encryption_mode(value: object, *, label: str = "encryption") -> EncryptionMode:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be one of: {ENCRYPTION_MODES_DISPLAY}.")
    token = value.strip().lower()
    match token:
        case "symmetric" | "s":
            return "symmetric"
        case "asymmetric" | "a":
            return "asymmetric"
        case _:
            raise ValueError(f"{label} must be one of: {ENCRYPTION_MODES_DISPLAY}.")
