from typing import Literal, TypedDict


class KilledTarget(TypedDict):
    action: Literal["session", "window", "pane"]
    session: str
    window: str
    detail: str
