import getpass
import os
import sys
from pathlib import Path

from typer._click.exceptions import UsageError

from stackops.utils.cli_utils.interaction import require_interactive


def read_secret_input(*, value: str | None, file: Path | None, env: str | None, prompt: str) -> str:
    if sum(source is not None for source in (value, file, env)) > 1:
        raise UsageError("Choose exactly one secret value, secret file/stdin, or environment-variable reference.")
    if file is not None:
        if file == Path("-") and sys.stdin.isatty():
            raise UsageError("Secret input from '-' requires piped or redirected stdin.")
        try:
            secret_text = sys.stdin.read() if file == Path("-") else file.expanduser().read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise UsageError("Could not read the secret input file as UTF-8 text.") from error
        value = secret_text.removesuffix("\n").removesuffix("\r")
    elif env is not None:
        value = os.environ.get(env)
        if value is None:
            raise UsageError(f"""Secret environment variable {env!r} is not set.""")
    elif value is None:
        require_interactive(f"""{prompt} Supply a secret file or environment-variable reference instead of prompting.""")
        value = getpass.getpass(prompt)
    if value is None or value == "":
        raise UsageError("The supplied secret must not be empty.")
    return value
