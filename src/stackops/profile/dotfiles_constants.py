from typing import Literal

type OsName = Literal["linux", "darwin", "windows"]

ALL_OS_VALUES: tuple[OsName, OsName, OsName] = ("linux", "darwin", "windows")
DEFAULT_OS_FILTER = ",".join(ALL_OS_VALUES)
OS_OUTPUT_ORDER: dict[OsName, int] = {value: index for index, value in enumerate(ALL_OS_VALUES)}
VALID_OS_VALUES: frozenset[OsName] = frozenset(ALL_OS_VALUES)
PACKAGED_SETTINGS_TOKEN_PREFIX = "CONFIG_ROOT/"
COLLECTED_SETTINGS_TOKEN_PREFIX = "DOTFILES_ROOT/"
STATUS_DETAIL_ROW_LIMIT = 25
