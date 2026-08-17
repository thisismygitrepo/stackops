from pathlib import Path
from platform import system
from typing import Never, cast

from rich import box
from rich.console import Console
from rich.panel import Panel

from stackops.scripts.python.helpers.helpers_network.ssh.ssh_add_key_posix import add_ssh_keys_posix
from stackops.scripts.python.helpers.helpers_network.ssh.ssh_add_key_windows import add_ssh_key_windows
from stackops.scripts.python.helpers.helpers_network.ssh.ssh_public_keys import (
    PublicKeyRecord,
    parse_public_key_records,
    read_public_key_file,
)


console = Console()
POSIX_SYSTEMS: tuple[str, str] = ("Linux", "Darwin")


def main(pub_path: str | None, pub_choose: bool, pub_val: bool, from_github: str | None, remote: str | None) -> None:
    source_count = sum((pub_path is not None, pub_choose, pub_val, from_github is not None))
    if source_count != 1:
        _exit_with_error(message="Choose exactly one public-key source: --path, --choose, --value, or --github.")

    try:
        records, source_description = _load_key_source(
            pub_path=pub_path,
            pub_choose=pub_choose,
            pub_val=pub_val,
            from_github=from_github,
        )
        if remote is not None:
            from stackops.scripts.python.helpers.helpers_network.ssh.ssh_deploy_key_remote import deploy_keys_to_remote

            if not deploy_keys_to_remote(remote_target=remote, records=records, password=None):
                raise SystemExit(1)
            return

        operating_system = system()
        if operating_system in POSIX_SYSTEMS:
            authorized_keys, added_count = add_ssh_keys_posix(records=records)
        elif operating_system == "Windows":
            authorized_keys, added_count = add_ssh_key_windows(records=records)
        else:
            raise NotImplementedError(f"SSH public-key authorization is unsupported on {operating_system}.")
    except SystemExit:
        raise
    except Exception as error:
        _exit_with_error(message=str(error))

    console.print(
        Panel(
            f"Source: {source_description}\n"
            f"Validated records: {len(records)}\n"
            f"New records: {added_count}\n"
            f"Authorization file: [green]{authorized_keys}[/green]",
            title="[bold green]SSH Key Authorization Complete[/bold green]",
            border_style="green",
            box=box.DOUBLE_EDGE,
        )
    )


def _load_key_source(
    pub_path: str | None,
    pub_choose: bool,
    pub_val: bool,
    from_github: str | None,
) -> tuple[list[PublicKeyRecord], str]:
    if pub_path is not None:
        path = Path(pub_path).expanduser().absolute()
        records = read_public_key_file(path=path)
        return records, str(path)

    if pub_choose:
        return _choose_public_key_files()

    if pub_val:
        pasted_value = input("Paste one SSH public-key record: ")
        records = parse_public_key_records(value=pasted_value, source="pasted value")
        if len(records) != 1:
            raise ValueError("--value accepts exactly one SSH public-key record.")
        return records, "pasted value (kept in memory)"

    if from_github is not None:
        return _load_github_public_keys(username=from_github), f"GitHub @{from_github}"

    raise ValueError("No public-key source was selected.")


def _choose_public_key_files() -> tuple[list[PublicKeyRecord], str]:
    ssh_directory = Path.home().joinpath(".ssh")
    available_paths = sorted(path for path in ssh_directory.glob("*.pub") if path.is_file())
    if not available_paths:
        raise ValueError("No public-key files were found in ~/.ssh.")

    from stackops.utils.options_utils.options import choose_from_options

    selected_paths = choose_from_options(
        options=available_paths,
        msg="Select public-key file(s) to authorize",
        multi=True,
        custom_input=False,
        header="",
        tail="",
        prompt="",
        default=None,
        tv=True,
        preview=None,
    )
    if not selected_paths:
        raise ValueError("Public-key selection was cancelled.")

    records: list[PublicKeyRecord] = []
    for path in selected_paths:
        records.extend(read_public_key_file(path=path))
    return records, f"{len(selected_paths)} selected public-key file(s)"


def _load_github_public_keys(username: str) -> list[PublicKeyRecord]:
    if username.strip() == "" or username != username.strip():
        raise ValueError("GitHub username must not be empty or surrounded by whitespace.")

    import requests

    response = requests.get(f"https://api.github.com/users/{username}/keys", timeout=10)
    if response.status_code != 200:
        raise RuntimeError(f"GitHub returned HTTP {response.status_code} for user {username!r}.")
    payload = cast(object, response.json())
    if not isinstance(payload, list):
        raise ValueError("GitHub returned an invalid public-key response.")

    records: list[PublicKeyRecord] = []
    for index, item_value in enumerate(payload, start=1):
        if not isinstance(item_value, dict):
            raise ValueError(f"GitHub key entry {index} is not an object.")
        item = cast(dict[object, object], item_value)
        key_value = item.get("key")
        if not isinstance(key_value, str):
            raise ValueError(f"GitHub key entry {index} has no textual key value.")
        item_records = parse_public_key_records(value=key_value, source=f"GitHub key entry {index}")
        if len(item_records) != 1:
            raise ValueError(f"GitHub key entry {index} does not contain exactly one public-key record.")
        records.extend(item_records)
    if not records:
        raise ValueError(f"GitHub user {username!r} has no public keys.")
    return records


def _exit_with_error(message: str) -> Never:
    console.print(Panel(message, title="[bold red]SSH Key Authorization Failed[/bold red]", border_style="red"))
    raise SystemExit(1)
