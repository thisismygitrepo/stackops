import re

_ENV_NAME_PATTERN: re.Pattern[str] = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def is_valid_env_name(name: str) -> bool:
    return _ENV_NAME_PATTERN.fullmatch(name) is not None
