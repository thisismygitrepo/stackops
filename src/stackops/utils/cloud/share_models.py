from typing import Literal, TypeAlias, TypedDict


ShareScope: TypeAlias = Literal["anonymous", "organization"]
ShareScopeChoice: TypeAlias = Literal["anonymous", "a", "organization", "o"]
ShareLinkType: TypeAlias = Literal["view", "edit", "embed"]
ShareLinkTypeChoice: TypeAlias = Literal["view", "v", "edit", "e", "embed", "m"]


class ShareLinkOptions(TypedDict):
    scope: ShareScope | None
    link_type: ShareLinkType | None
