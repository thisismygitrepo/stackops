from typing import Final

from support.models import ManagedLoginAgentSupport


SUPPORT: Final[ManagedLoginAgentSupport] = ManagedLoginAgentSupport(
    agent="copilot",
    display_name="GitHub Copilot CLI",
    aliases=("c",),
    reason=(
        "OAuth credentials use the operating-system credential store by default, and environment variables or GitHub CLI "
        "authentication can override stored credentials; no safe file-backed profile is verified."
    ),
    guidance="Run `copilot login` to authenticate, then use `/user list` and `/user switch` inside Copilot to manage accounts.",
)
