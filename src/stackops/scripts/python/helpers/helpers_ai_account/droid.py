from typing import Final

from stackops.scripts.python.helpers.helpers_ai_account.models import ManagedLoginAgentSupport


SUPPORT: Final[ManagedLoginAgentSupport] = ManagedLoginAgentSupport(
    agent="droid",
    display_name="Factory Droid",
    aliases=("d",),
    reason=(
        "Factory Droid has no single portable credential artifact: browser login uses an encrypted file with either a sibling "
        "key file or native keyring state, while API-key authentication uses an environment variable."
    ),
    guidance=(
        "Run droid and use /login for browser authentication, or provide FACTORY_API_KEY through the shell or a secret manager. "
        "Use /logout followed by /login to change the browser-authenticated account."
    ),
)
