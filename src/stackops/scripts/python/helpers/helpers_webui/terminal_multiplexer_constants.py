from typing import Final, Literal

from stackops.utils.schemas.config.multiplexer_types import SessionMultiplexer

type MultiplexerRole = Literal["session", "agent"]
# What else follows the session default, beyond launching, listing, opening and ending sessions, which every multiplexer can do.
type MultiplexerCapability = Literal["batch", "save", "browsers", "mounts", "agents"]

MULTIPLEXER_CAPABILITIES: Final[tuple[MultiplexerCapability, ...]] = ("batch", "save", "browsers", "mounts", "agents")
# `cloud mount` lists the multiplexers it takes inside its own signature, with no name to import, so the two are repeated here.
CLOUD_MOUNT_MULTIPLEXERS: Final[tuple[SessionMultiplexer, ...]] = ("tmux", "tuios")
# The card shows a few names and the count; a machine with dozens of sessions does not send them all.
RUNNING_NAMES_LIMIT: Final[int] = 12
