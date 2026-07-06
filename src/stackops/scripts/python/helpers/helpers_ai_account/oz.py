from typing import Final

from stackops.scripts.python.helpers.helpers_ai_account.models import ManagedLoginAgentSupport


SUPPORT: Final[ManagedLoginAgentSupport] = ManagedLoginAgentSupport(
    agent="oz",
    display_name="Oz",
    aliases=("z",),
    reason=(
        "Oz stores interactive credentials in platform-native secure storage and does not persist API-key authentication "
        "as a portable file."
    ),
    guidance="Use `oz login` for interactive authentication or set `WARP_API_KEY` for non-interactive authentication.",
)
