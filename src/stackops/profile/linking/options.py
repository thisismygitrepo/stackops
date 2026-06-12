from typing import Literal, TypeAlias

SENSITIVITY_LOOSE: TypeAlias = Literal["private", "p", "public", "b", "all", "a"]
SENSITIVITY_STRICT: TypeAlias = Literal["private", "public", "all"]
SENSITIVITY_MAP: dict[SENSITIVITY_LOOSE, SENSITIVITY_STRICT] = {
    "private": "private",
    "p": "private",
    "public": "public",
    "b": "public",
    "all": "all",
    "a": "all",
}

CONFIG_SOURCE_LOOSE: TypeAlias = Literal["library", "l", "user", "u", "all", "a"]
CONFIG_SOURCE_STRICT: TypeAlias = Literal["library", "user", "all"]
CONFIG_SOURCE_MAP: dict[CONFIG_SOURCE_LOOSE, CONFIG_SOURCE_STRICT] = {
    "library": "library",
    "l": "library",
    "user": "user",
    "u": "user",
    "a": "all",
    "all": "all",
}

CONFIG_FILE_SOURCE_LOOSE: TypeAlias = Literal["library", "l", "user", "u"]
CONFIG_FILE_SOURCE_STRICT: TypeAlias = Literal["library", "user"]
CONFIG_FILE_SOURCE_MAP: dict[CONFIG_FILE_SOURCE_LOOSE, CONFIG_FILE_SOURCE_STRICT] = {
    "library": "library",
    "l": "library",
    "user": "user",
    "u": "user",
}

METHOD_LOOSE: TypeAlias = Literal["symlink", "s", "copy", "c"]
METHOD_STRICT: TypeAlias = Literal["symlink", "copy"]
METHOD_MAP: dict[METHOD_LOOSE, METHOD_STRICT] = {
    "symlink": "symlink",
    "s": "symlink",
    "copy": "copy",
    "c": "copy",
}

DIRECTION_LOOSE: TypeAlias = Literal["up", "u", "down", "d"]
DIRECTION_STRICT: TypeAlias = Literal["up", "down"]
DIRECTION_MAP: dict[DIRECTION_LOOSE, DIRECTION_STRICT] = {
    "up": "up",
    "u": "up",
    "down": "down",
    "d": "down",
}
