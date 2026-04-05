"""Like yadm and dotter."""

from pathlib import Path
import shutil
import subprocess
from typing import Annotated, Literal

import typer

from machineconfig.profile.dotfiles_mapper import (
    DEFAULT_DOTFILE_MAPPER_HEADER,
    DEFAULT_OS_FILTER,
    LIBRARY_MAPPER_PATH,
    USER_MAPPER_PATH,
    RawMapperEntry,
    dump_dotfiles_mapper,
    load_dotfiles_mapper,
    normalize_os_filter,
    write_dotfiles_mapper,
)
from machineconfig.profile.create_links_export import METHOD_LOOSE, METHOD_MAP, ON_CONFLICT_LOOSE, ON_CONFLICT_MAPPER
from machineconfig.utils.source_of_truth import CONFIG_ROOT
from machineconfig.utils.path_extended import PathExtended

BACKUP_ROOT_PRIVATE = Path.home().joinpath("dotfiles/machineconfig/mapper/files")
BACKUP_ROOT_PUBLIC = Path(CONFIG_ROOT).joinpath("dotfiles/mapper")


def _format_home_relative_path(path: Path) -> str:
    home = Path.home()
    if path.is_relative_to(home):
        return f"~/{path.relative_to(home).as_posix()}"
    return path.as_posix()


def _format_self_managed_mapper_path(path: Path) -> str:
    config_root = Path(CONFIG_ROOT).expanduser().resolve()
    resolved_path = path.expanduser().resolve(strict=False)
    if resolved_path == config_root:
        return "CONFIG_ROOT"
    if resolved_path.is_relative_to(config_root):
        relative_path = resolved_path.relative_to(config_root)
        return f"CONFIG_ROOT/{relative_path.as_posix()}"
    return _format_home_relative_path(path)


def _build_entry_name(original_path: Path) -> str:
    return original_path.stem.replace(".", "_").replace("-", "_")


def _build_mapper_entry(
    original_path: Path,
    self_managed_path: Path,
    method: Literal["symlink", "copy"],
    is_contents: bool,
    os_filter: str,
) -> RawMapperEntry:
    entry: RawMapperEntry = {
        "original": _format_home_relative_path(original_path),
        "self_managed": _format_self_managed_mapper_path(self_managed_path),
        "os": normalize_os_filter(os_filter),
    }
    if is_contents:
        entry["contents"] = True
    if method == "copy":
        entry["copy"] = True
    return entry


def _build_mapper_preview(section: str, entry_name: str, entry: RawMapperEntry) -> str:
    preview = dump_dotfiles_mapper(
        mapper={section: {entry_name: entry}},
        header="",
    )
    return preview.rstrip()


def _write_to_user_mapper(
    section: str,
    entry_name: str,
    original_path: Path,
    self_managed_path: Path,
    method: Literal["symlink", "copy"],
    is_contents: bool,
    os_filter: str,
) -> tuple[Path, RawMapperEntry]:
    mapper_path = USER_MAPPER_PATH
    mapper_path.parent.mkdir(parents=True, exist_ok=True)
    mapper = load_dotfiles_mapper(mapper_path) if mapper_path.exists() else {}
    section_entries = dict(mapper.get(section, {}))
    entry = _build_mapper_entry(
        original_path=original_path,
        self_managed_path=self_managed_path,
        method=method,
        is_contents=is_contents,
        os_filter=os_filter,
    )
    section_entries[entry_name] = entry
    mapper[section] = section_entries
    write_dotfiles_mapper(
        path=mapper_path,
        mapper=mapper,
        header=DEFAULT_DOTFILE_MAPPER_HEADER,
    )
    return mapper_path, entry

def record_mapping(orig_path: Path, new_path: Path, method: METHOD_LOOSE, section: str, os_filter: str) -> None:
    entry_name = _build_entry_name(orig_path)
    method_resolved = METHOD_MAP[method]
    mapper_file, entry = _write_to_user_mapper(
        section=section,
        entry_name=entry_name,
        original_path=orig_path,
        self_managed_path=new_path,
        method=method_resolved,
        is_contents=False,
        os_filter=os_filter,
    )
    preview = _build_mapper_preview(section=section, entry_name=entry_name, entry=entry)
    from rich.console import Console
    from rich.panel import Panel
    console = Console()
    console.print(
        Panel(
            f"📝 Mapping recorded in: [cyan]{mapper_file}[/cyan]\n\n{preview}",
            title="Mapper Entry Saved",
            border_style="cyan",
            padding=(1, 2),
        )
    )


def get_backup_path(orig_path: Path, sensitivity: Literal["private", "v", "public", "b"], destination: str | None, shared: bool) -> Path:
    match sensitivity:
        case "private" | "v":
            backup_root = BACKUP_ROOT_PRIVATE
        case "public" | "b":
            backup_root = BACKUP_ROOT_PUBLIC
        case _:
            raise ValueError(f"Unknown sensitivity: {sensitivity}")
    if destination is None:
        if shared:
            new_path = backup_root.joinpath("shared").joinpath(orig_path.name)
        else:
            new_path = backup_root.joinpath(orig_path.relative_to(Path.home()))
    else:
        if shared:
            dest_path = Path(destination).expanduser().absolute()
            new_path = dest_path.joinpath("shared").joinpath(orig_path.name)
        else:
            dest_path = Path(destination).expanduser().absolute()
            new_path = dest_path.joinpath(orig_path.name)
    return new_path


def get_original_path_from_backup_path(backup_path: Path, sensitivity: Literal["private", "v", "public", "b"], destination: str | None, shared: bool) -> Path:
    match sensitivity:
        case "private" | "v":
            backup_root = BACKUP_ROOT_PRIVATE
        case "public" | "b":
            backup_root = BACKUP_ROOT_PUBLIC
        case _:
            raise ValueError(f"Unknown sensitivity: {sensitivity}")
    if destination is None:
        if shared:
            relative_part = backup_path.relative_to(backup_root.joinpath("shared"))
        else:
            relative_part = backup_path.relative_to(backup_root)
        original_path = Path.home().joinpath(relative_part)
    else:
        dest_path = Path(destination).expanduser().absolute()
        if shared:
            relative_part = backup_path.relative_to(dest_path.joinpath("shared"))
        else:
            relative_part = backup_path.relative_to(dest_path)
        original_path = Path.home().joinpath(relative_part)
    return original_path


def register_dotfile(
    file: Annotated[str, typer.Argument(help="file/folder path.")],
    method: Annotated[METHOD_LOOSE, typer.Option(..., "--method", "-m", help="Method to use for linking files")] = "copy",
    on_conflict: Annotated[ON_CONFLICT_LOOSE, typer.Option(..., "--on-conflict", "-o", help="Action to take on conflict")] = "throw-error",
    sensitivity: Annotated[Literal["private", "v", "public", "b"], typer.Option(..., "--sensitivity", "-s", help="Sensitivity of the config file.")] = "private",
    destination: Annotated[str | None, typer.Option("--destination", "-d", help="destination folder (override the default, use at your own risk)")] = None,
    section: Annotated[str, typer.Option("--section", "-se", help="Section name in mapper_dotfiles.yaml to record this mapping.")] = "default",
    os_filter: Annotated[str, typer.Option("--os", help="Comma-separated OS list from: linux,darwin,windows.")] = DEFAULT_OS_FILTER,
    shared: Annotated[bool, typer.Option("--shared", "-sh", help="Whether the config file is shared across destinations directory.")] = False,
    record: Annotated[bool, typer.Option("--record", "-r", help="Record the mapping in user's mapper.yaml")] = True,
    ) -> None:
    from rich.console import Console
    from rich.panel import Panel
    from machineconfig.utils.links import symlink_map, copy_map
    console = Console()
    orig_path = Path(file).expanduser().absolute()
    new_path = get_backup_path(orig_path=orig_path, sensitivity=sensitivity, destination=destination, shared=shared)
    orig_path_extended = PathExtended(orig_path)
    new_path_extended = PathExtended(new_path)
    if not orig_path.exists() and not new_path.exists():
        console.print(f"[red]Error:[/] Neither original file nor self-managed file exists:\n  Original: {orig_path}\n  Self-managed: {new_path}")
        raise typer.Exit(code=1)
    new_path.parent.mkdir(parents=True, exist_ok=True)
    match method:
        case "copy" | "c":
            try:
                copy_map(config_file_default_path=orig_path_extended, config_file_self_managed_path=new_path_extended, on_conflict=ON_CONFLICT_MAPPER[on_conflict])
            except Exception as e:
                msg = typer.style("Error: ", fg=typer.colors.RED) + str(e)
                typer.echo(msg)
                raise typer.Exit(code=1) from e
        case "symlink" | "s":
            try:
                symlink_map(config_file_default_path=orig_path_extended, config_file_self_managed_path=new_path_extended, on_conflict=ON_CONFLICT_MAPPER[on_conflict])
            except Exception as e:
                msg = typer.style("Error: ", fg=typer.colors.RED) + str(e)
                typer.echo(msg)
                raise typer.Exit(code=1) from e
        case _:
            raise ValueError(f"Unknown method: {method}")
    if record:
        record_mapping(orig_path=orig_path, new_path=new_path, method=method, section=section, os_filter=os_filter)
        return
    entry_name = _build_entry_name(orig_path)
    preview = _build_mapper_preview(
        section=section,
        entry_name=entry_name,
        entry=_build_mapper_entry(
            original_path=orig_path,
            self_managed_path=new_path,
            method=METHOD_MAP[method],
            is_contents=False,
            os_filter=os_filter,
        ),
    )
    console.print(
        Panel(
            "\n".join(
                [
                    "✅ Dotfile mapping applied successfully.",
                    "🔄 Add the following YAML to mapper.yaml to persist this mapping:",
                    "",
                    preview,
                ]
            ),
            title="Mapping Preview",
            border_style="green",
            padding=(1, 2),
        )
    )


def edit_dotfile(
    editor: Annotated[
        Literal["nano", "hx", "code"],
        typer.Option("--editor", "-e", help="📝 Editor to open the dotfiles mapper.yaml file."),
    ] = "hx",
    repo: Annotated[
        Literal["library", "l", "user", "u"],
        typer.Option("--repo", "-r", help="📁 Which mapper file to edit: 'user' or 'library'."),
    ] = "user",
) -> None:
    from machineconfig.profile.create_links_export import REPO_MAP

    repo_key = REPO_MAP[repo]
    if repo_key == "user":
        file_path = USER_MAPPER_PATH
        file_path.parent.mkdir(parents=True, exist_ok=True)
        if not file_path.exists():
            write_dotfiles_mapper(path=file_path, mapper={}, header=DEFAULT_DOTFILE_MAPPER_HEADER)
    else:
        file_path = LIBRARY_MAPPER_PATH
        if not file_path.exists():
            msg = typer.style("Error: ", fg=typer.colors.RED) + f"Library mapper file not found: {file_path}"
            typer.echo(msg)
            raise typer.Exit(code=1)

    editor_bin = shutil.which(editor)
    if editor_bin is None:
        msg = typer.style("Error: ", fg=typer.colors.RED) + f"Editor '{editor}' is not available on PATH."
        typer.echo(msg)
        raise typer.Exit(code=1)

    result = subprocess.run([editor_bin, str(file_path)], check=False)
    if result.returncode != 0:
        msg = typer.style("Error: ", fg=typer.colors.RED) + f"Editor exited with status code {result.returncode}."
        typer.echo(msg)
        raise typer.Exit(code=result.returncode)


def export_dotfiles(
        pwd: Annotated[str, typer.Argument(..., help="Password for zip encryption")],
        over_internet: Annotated[bool, typer.Option("--over-internet", "-i", help="Use internet-based transfer (wormhole-magic)")] = False,
        over_ssh: Annotated[bool, typer.Option("--over-ssh", "-s", help="Use SSH-based transfer (scp) to a remote machine")] = False,
        ):
    """🔗 Export dotfiles for migration to new machine."""
    if over_ssh:
        code_sample = """ftpx ~/dotfiles user@remote_host:^ -z"""
        print("🔗 Exporting dotfiles via SSH-based transfer (scp).")
        print(f"💡 Run the following command on your local machine to copy dotfiles to the remote machine:\n{code_sample}")
        remote_address = typer.prompt("Enter the remote machine address (user@host) to copy dotfiles to ")
        code_concrete = f"fptx ~/dotfiles {remote_address}:^ -z"
        from machineconfig.utils.code import run_shell_script
        run_shell_script(code_concrete, display_script=True, clean_env=False)
    dotfiles_dir = Path.home().joinpath("dotfiles")
    if not dotfiles_dir.exists() or not dotfiles_dir.is_dir():
        print(f"❌ Dotfiles directory does not exist: {dotfiles_dir}")
        raise typer.Exit(code=1)
    dotfiles_zip = Path.home().joinpath("dotfiles.zip")
    if dotfiles_zip.exists():
        dotfiles_zip.unlink()
    zipfile = shutil.make_archive(base_name=str(dotfiles_zip)[:-4], format="zip", root_dir=str(dotfiles_dir), base_dir=".", verbose=False)
    from machineconfig.utils.io import encrypt
    zipfile_enc_bytes = encrypt(
        msg=Path(zipfile).read_bytes(),
        pwd=pwd,
    )
    Path(zipfile).unlink()
    zipfile_enc_path = Path(rf"{zipfile}.enc")
    if zipfile_enc_path.exists():
        zipfile_enc_path.unlink()
    zipfile_enc_path.write_bytes(zipfile_enc_bytes)
    print(f"✅ Dotfiles exported to: {zipfile_enc_path}")
    if over_internet:
        # rm ~/dotfiles.zip || true
        # ouch c ~/dotfiles dotfiles.zip
        # # INSECURE OVER INTERNET: uvx wormhole-magic send ~/dotfiles.zip
        raise NotImplementedError("Internet-based transfer not yet implemented.")
    # devops network share-server --no-auth ./dotfiles.zip
    from machineconfig.scripts.python.helpers.helpers_devops import cli_share_server
    from machineconfig.scripts.python.helpers.helpers_network.address import select_lan_ipv4

    localipv4 = select_lan_ipv4(prefer_vpn=False)
    port = 8888
    msg = f"""On the remote machine, run the following:
d c i -u http://{localipv4}:{port} -p {pwd}
"""
    from machineconfig.utils.accessories import display_with_flashy_style

    display_with_flashy_style(msg=msg, title="Remote Machine Instructions")
    cli_share_server.web_file_explorer(
        path=str(zipfile_enc_path),
        no_auth=True,
        port=port,
        # bind_address="
    )


def import_dotfiles(
        url: Annotated[str | None, typer.Option(..., "--url", "-u", help="URL or local path to the encrypted dotfiles zip")] = None,
        pwd: Annotated[str | None, typer.Option(..., "--pwd", "-p", help="Password for zip decryption")] = None,
        use_ssh: Annotated[bool, typer.Option("--use-ssh", "-s", help="Use SSH-based transfer (scp) from a remote machine that has dotfiles.")]=False,
        ):  
    # # INSECURE cd $HOME; uvx wormhole-magic receive dotfiles.zip.enc --accept-file
    # ☁️  [bold blue]Method 3: USING INTERNET SECURE SHARE[/bold blue]
    #     [dim]cd ~
    #     cloud copy SHARE_URL . --config ss[/dim]
    if use_ssh:
        print("🔗 Importing dotfiles via SSH-based transfer (scp).")
        code = """cloud ftpx $USER@$(hostname):^ ~/dotfiles -z"""
        print(f"💡 Run the following command on the remote machine that has the dotfiles:\n{code}")
        url = typer.prompt("Enter the remote machine address (user@host) to copy dotfiles from ")

        code_concrete = f"cloud ftpx {url}:^ ~/dotfiles -z"
        from machineconfig.utils.code import run_shell_script
        run_shell_script(code_concrete, display_script=True, clean_env=False)

        print("✅ Dotfiles copied via SSH.")
        return
    if url is None:
        url = typer.prompt("Enter the URL or local path to the encrypted dotfiles zip (e..g 192.168.20.4:8888) ")
    if pwd is None:
        pwd = typer.prompt("Enter the password for zip decryption", hide_input=True)
    from machineconfig.scripts.python.helpers.helpers_utils.download import download
    downloaded_file = download(url=url, decompress=False, output_dir=str(Path.home()))
    if downloaded_file is None or not downloaded_file.exists():
        print(f"❌ Failed to download file from URL: {url}")
        raise typer.Exit(code=1)
    zipfile_enc_path = downloaded_file
    from machineconfig.utils.io import decrypt
    zipfile_bytes = decrypt(
        token=zipfile_enc_path.read_bytes(),
        pwd=pwd,
    )
    zipfile_path = Path(str(zipfile_enc_path)[:-4])
    if zipfile_path.exists():
        print(f"⚠️  WARNING: Overwriting existing file: {zipfile_path}")
        zipfile_path.unlink()
    zipfile_path.write_bytes(zipfile_bytes)
    print(f"✅ Decrypted zip file saved to: {zipfile_path}")
    import zipfile
    if Path.home().joinpath("dotfiles").exists():
        print(f"⚠️  WARNING: Overwriting existing directory: {Path.home().joinpath('dotfiles')}")
        shutil.rmtree(Path.home().joinpath("dotfiles"))
    with zipfile.ZipFile(zipfile_path, 'r') as zip_ref:
        zip_ref.extractall(Path.home().joinpath("dotfiles"))
    print(f"✅ Dotfiles extracted to: {Path.home().joinpath('dotfiles')}")
    zipfile_path.unlink()


def arg_parser() -> None:
    typer.run(register_dotfile)


if __name__ == "__main__":
    arg_parser()
