from typing import cast

import typer

from stackops.scripts.python.helpers.helpers_webui.terminal_multiplexer_views import MultiplexerProblem, read_settings
from stackops.utils.default_multiplexer import resolve_agent_multiplexer, resolve_session_multiplexer
from stackops.utils.schemas.config.config_types import StackOpsConfigValues
from stackops.utils.schemas.config.multiplexer_types import AGENT_MULTIPLEXERS, SESSION_MULTIPLEXERS


# Saves one default with the function `devops config setup multiplexer` saves with, and leaves the other as it is. A design choice: the command
# always writes both, which would mark a default nobody picked as the person's own choice. The CLI's resolvers refuse a multiplexer this system
# cannot run, so that rule is theirs and not repeated here.
def save_multiplexer_default(body: object) -> None | MultiplexerProblem:
    from stackops.scripts.python.helpers.helpers_devops.cli_config_setup_config import write_stackops_config

    fields = cast(dict[str, object], body) if isinstance(body, dict) else {}
    role, name = fields.get("role"), fields.get("name")
    values: StackOpsConfigValues
    try:
        match role:
            case "session" if name in SESSION_MULTIPLEXERS:
                values = {"default_session_multiplexer": resolve_session_multiplexer(multiplexer=name)}
            case "agent" if name in AGENT_MULTIPLEXERS:
                values = {"default_agent_multiplexer": resolve_agent_multiplexer(multiplexer=name)}
            case _:
                return MultiplexerProblem(status=400, message="`role` must be session or agent, and `name` a multiplexer that role can use.")
    except ValueError as error:
        return MultiplexerProblem(status=409, message=str(error))
    settings = read_settings()
    match settings:
        case MultiplexerProblem():
            return settings
        case _:
            try:
                write_stackops_config(existing_config=settings, values=values)
            except OSError as error:
                return MultiplexerProblem(status=500, message=f"""The settings file could not be written: {error}""")
            # The CLI's writer prints its reason and exits where it will not write; the reason is in the server's own output.
            except typer.Exit:
                return MultiplexerProblem(status=500, message="StackOps would not write the settings file. The server's output says why.")
    return None
