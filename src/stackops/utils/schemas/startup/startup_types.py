from typing import Literal, TypedDict

from stackops.profile.dotfiles_constants import OsName

type StartupKind = Literal["script", "layout"]
type StartupWhen = Literal["login", "boot"]
type StartupFileVersion = Literal["0.1"]


class StartupEntryConfig(TypedDict):
    kind: StartupKind
    name: str
    os: list[OsName]
    when: StartupWhen


class StartupFile(TypedDict):
    version: StartupFileVersion
    entries: list[StartupEntryConfig]
