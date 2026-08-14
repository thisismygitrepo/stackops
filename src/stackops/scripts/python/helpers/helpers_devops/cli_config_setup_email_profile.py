from pathlib import Path
from typing import Literal, TypedDict, cast

import typer

from stackops.secrets.models import Login, SecretsFile


EMAIL_SECRET_KEYS: tuple[str, str, str, str, str] = ("email_add", "password", "encryption", "smtp_host", "smtp_port")
type EmailEncryption = Literal["tls", "ssl"]


class NewEmailProfile(TypedDict):
    login: Login
    sender: str


def load_email_profiles(secrets_path: Path) -> tuple[SecretsFile | None, dict[str, str]]:
    from stackops.scripts.python.helpers.helpers_devops.cli_config_setup_config import exit_with_setup_error
    from stackops.secrets.loader import SecretsSchemaError, load_secrets_file

    if not secrets_path.exists():
        return None, {}
    if not secrets_path.is_file():
        exit_with_setup_error(f"Global secrets path exists but is not a file: {secrets_path}")
    try:
        secrets_file = load_secrets_file(secrets_path)
    except (OSError, SecretsSchemaError) as exc:
        exit_with_setup_error(f"Global secrets cannot be safely read or updated:\n{exc}")

    profiles: dict[str, str] = {}
    duplicate_names: set[str] = set()
    normalized_names: dict[str, str] = {}
    ambiguous_names: set[str] = set()
    for login in secrets_file["entries"]:
        for secret in login["secrets"]:
            key_values = secret["keyValues"]
            if not all(key in key_values for key in EMAIL_SECRET_KEYS):
                continue
            sender = key_values["email_add"]
            password = key_values["password"]
            encryption = key_values["encryption"]
            smtp_host = key_values["smtp_host"]
            if not all(isinstance(value, str) and value.strip() != "" for value in (sender, password, encryption, smtp_host)):
                exit_with_setup_error(f"Email profile {login['name']!r} has an empty or non-string SMTP value in {secrets_path}")
            assert isinstance(sender, str)
            assert isinstance(encryption, str)
            if encryption.lower() not in {"tls", "ssl"}:
                exit_with_setup_error(f"Email profile {login['name']!r} must use 'tls' or 'ssl' encryption in {secrets_path}")
            try:
                smtp_port = int(str(key_values["smtp_port"]))
            except ValueError:
                exit_with_setup_error(f"Email profile {login['name']!r} has a non-numeric smtp_port in {secrets_path}")
            if not 1 <= smtp_port <= 65535:
                exit_with_setup_error(f"Email profile {login['name']!r} has an smtp_port outside 1-65535 in {secrets_path}")
            if login["name"] in profiles:
                duplicate_names.add(login["name"])
            profiles[login["name"]] = sender
            normalized_name = login["name"].casefold()
            previous_name = normalized_names.get(normalized_name)
            if previous_name is not None and previous_name != login["name"]:
                ambiguous_names.update((previous_name, login["name"]))
            normalized_names[normalized_name] = login["name"]

    if duplicate_names:
        exit_with_setup_error(
            "Each email profile name must match exactly one SMTP secret bundle. Duplicate profiles: "
            + ", ".join(sorted(duplicate_names))
        )
    if ambiguous_names:
        exit_with_setup_error(
            "Email profile names must also be unique when case is ignored for interactive selection: "
            + ", ".join(sorted(ambiguous_names))
        )
    return secrets_file, profiles


def prompt_new_email_profile(
    *,
    existing_login_names: set[str],
    configured_profile: str | None,
    configured_recipient: str | None,
) -> NewEmailProfile:
    from stackops.scripts.python.helpers.helpers_devops.register_interactive import ask_choice, ask_text

    default_name = configured_profile if configured_profile is not None else "default"
    normalized_existing_names = {name.casefold() for name in existing_login_names}
    while True:
        profile_name = ask_text(
            "Email profile name",
            help_text="This name identifies the SMTP credentials in the global StackOps secrets file.",
            default=default_name,
        )
        assert profile_name is not None
        if profile_name.casefold() not in normalized_existing_names:
            break
        typer.echo(f"A secrets login matching {profile_name!r} already exists. Choose a unique profile name.")

    sender = ask_text(
        "Sender email address",
        help_text="The account address used to authenticate with the SMTP server and send notifications.",
        default=configured_recipient,
    )
    assert sender is not None
    encryption = cast(
        EmailEncryption,
        ask_choice(
            "SMTP encryption",
            help_text="Choose TLS for STARTTLS or SSL for an immediately encrypted connection.",
            choices=("tls", "ssl"),
            default="tls",
        ),
    )
    smtp_host = ask_text(
        "SMTP host",
        help_text="The SMTP server hostname supplied by the email provider.",
        default=None,
    )
    assert smtp_host is not None
    default_port = 587 if encryption == "tls" else 465
    while True:
        smtp_port = int(typer.prompt("SMTP port", default=default_port, type=int))
        if 1 <= smtp_port <= 65535:
            break
        typer.echo("SMTP port must be between 1 and 65535.")
    password = str(
        typer.prompt(
            "SMTP password or app password",
            hide_input=True,
            confirmation_prompt=True,
            show_default=False,
        )
    )
    login: Login = {
        "name": profile_name,
        "secrets": [
            {
                "name": "smtp",
                "tags": ["email"],
                "scopes": [],
                "keyValues": {
                    "email_add": sender,
                    "password": password,
                    "encryption": encryption,
                    "smtp_host": smtp_host,
                    "smtp_port": str(smtp_port),
                },
            }
        ],
    }
    return {
        "login": login,
        "sender": sender,
    }


def write_new_email_profile(secrets_path: Path, secrets_file: SecretsFile | None, profile: NewEmailProfile) -> None:
    import stackops.secrets.assets as secrets_assets
    from stackops.secrets.constants import SECRETS_FILE_VERSION
    from stackops.secrets.writer import create_secrets_file, replace_secrets_file
    from stackops.utils.path_reference import get_path_reference_path

    schema_path = secrets_path.with_name(secrets_assets.SECRETS_SCHEMA_PATH_REFERENCE)
    if schema_path.exists() and not schema_path.is_file():
        raise ValueError(f"Secrets schema path exists but is not a file: {schema_path}")
    schema_content: str | None = None
    if not schema_path.exists():
        schema_source_path = get_path_reference_path(
            module=secrets_assets,
            path_reference=secrets_assets.SECRETS_SCHEMA_PATH_REFERENCE,
        )
        schema_content = schema_source_path.read_text(encoding="utf-8")

    if secrets_file is None:
        created_file: SecretsFile = {
            "$schema": f"./{secrets_assets.SECRETS_SCHEMA_PATH_REFERENCE}",
            "version": SECRETS_FILE_VERSION,
            "entries": [profile["login"]],
        }
        create_secrets_file(secrets_path=secrets_path, secrets_file=created_file)
    else:
        secrets_file["entries"].append(profile["login"])
        replace_secrets_file(secrets_path=secrets_path, secrets_file=secrets_file)
    if schema_content is not None:
        schema_path.write_text(schema_content, encoding="utf-8")
