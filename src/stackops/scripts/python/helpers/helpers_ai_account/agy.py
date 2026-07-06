from typing import Final

from stackops.scripts.python.helpers.helpers_ai_account.models import ManagedLoginAgentSupport


SUPPORT: Final[ManagedLoginAgentSupport] = ManagedLoginAgentSupport(
    agent="agy",
    display_name="Google Antigravity CLI",
    aliases=("a", "antigravity"),
    reason="Antigravity CLI stores session tokens in the operating system's native secure keyring.",
    guidance="Use Antigravity CLI's Google Sign-In flow to change accounts and /logout to remove the active keyring session.",
)
