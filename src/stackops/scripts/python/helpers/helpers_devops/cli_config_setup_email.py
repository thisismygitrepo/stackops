import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

EMAIL_SETUP_HELP = "Select or create an SMTP profile and save the default recipient."


def setup_email() -> None:
    import stackops.utils.schemas.config as config_assets
    from stackops.scripts.python.helpers.helpers_devops.cli_config_setup_config import (
        exit_with_setup_error,
        load_stackops_config_for_setup,
        write_stackops_config,
    )
    from stackops.scripts.python.helpers.helpers_devops.cli_config_setup_email_profile import (
        NewEmailProfile,
        load_email_profiles,
        prompt_new_email_profile,
        write_new_email_profile,
    )
    from stackops.scripts.python.helpers.helpers_devops.register_interactive import ask_choice, ask_text
    from stackops.secrets.paths import SECRETS_DOFILE
    from stackops.utils.source_of_truth import DOTFILES_STACKOPS_CONFIG_PATH

    config_path = DOTFILES_STACKOPS_CONFIG_PATH
    schema_path = config_path.with_name(config_assets.CONFIG_SCHEMA_PATH_REFERENCE)
    if schema_path.exists() and not schema_path.is_file():
        exit_with_setup_error(f"StackOps schema path exists but is not a file: {schema_path}")
    existing_config = load_stackops_config_for_setup(config_path=config_path)
    configured_profile = existing_config.get("default_email_config") if existing_config is not None else None
    configured_recipient = existing_config.get("default_email_address") if existing_config is not None else None
    secrets_file, email_profiles = load_email_profiles(secrets_path=SECRETS_DOFILE)

    new_profile: NewEmailProfile | None = None
    if email_profiles and typer.confirm("Use an existing SMTP profile?", default=True):
        profile_names = tuple(sorted(email_profiles))
        default_profile = configured_profile if configured_profile in email_profiles else profile_names[0]
        selected_profile = ask_choice(
            "SMTP profile",
            help_text="Choose credentials already stored in the global StackOps secrets file.",
            choices=profile_names,
            default=default_profile,
        )
        sender = email_profiles[selected_profile]
    else:
        existing_login_names = {entry["name"] for entry in secrets_file["entries"]} if secrets_file is not None else set()
        new_profile = prompt_new_email_profile(
            existing_login_names=existing_login_names,
            configured_profile=configured_profile,
            configured_recipient=configured_recipient,
        )
        selected_profile = new_profile["login"]["name"]
        sender = new_profile["sender"]

    recipient = ask_text(
        "Default recipient",
        help_text="Notifications use this address when a command does not provide a recipient.",
        default=configured_recipient if configured_recipient is not None else sender,
    )
    assert recipient is not None

    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="bold cyan", no_wrap=True)
    summary.add_column(overflow="fold")
    summary.add_row("SMTP profile", selected_profile)
    summary.add_row("Profile action", "Create" if new_profile is not None else "Reuse")
    summary.add_row("Sender", sender)
    summary.add_row("Default recipient", recipient)
    summary.add_row("Config", config_path.as_posix())
    summary.add_row("Secrets", SECRETS_DOFILE.as_posix())
    console = Console()
    console.print(Panel(summary, title="Email Configuration", border_style="cyan", padding=(1, 2)))
    if not typer.confirm("Write this configuration?", default=True):
        raise typer.Exit(code=0)

    if new_profile is not None:
        try:
            write_new_email_profile(secrets_path=SECRETS_DOFILE, secrets_file=secrets_file, profile=new_profile)
        except (OSError, ValueError) as exc:
            exit_with_setup_error(f"Could not write the email profile: {exc}")
    write_stackops_config(
        config_path=config_path,
        schema_path=schema_path,
        existing_config=existing_config,
        values={
            "default_email_config": selected_profile,
            "default_email_address": recipient,
        },
    )
    console.print(Panel("Default email notifications are configured.", title="Configuration Saved", border_style="green", padding=(1, 2)))
