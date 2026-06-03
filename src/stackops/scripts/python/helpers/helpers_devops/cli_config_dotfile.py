"""Like yadm and dotter."""

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Annotated, Literal
import zipfile

import typer

from stackops.profile.dotfiles_mapper import (
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
from stackops.profile.create_links_export import METHOD_LOOSE, METHOD_MAP, ON_CONFLICT_LOOSE, ON_CONFLICT_MAPPER
from stackops.utils.source_of_truth import CONFIG_ROOT, DOTFILES_MAPPER_FILES_ROOT, DOTFILES_ROOT, DOTFILES_ZIP_PATH

BACKUP_ROOT_FLAT = DOTFILES_MAPPER_FILES_ROOT
FLAT_PATH_HASH_LENGTH = 16


def _format_home_relative_path(path: Path) -> str:
    home = Path.home()
    if path.is_relative_to(home):
        return f"~/{path.relative_to(home).as_posix()}"
    return path.as_posix()


def _format_self_managed_mapper_path(path: Path) -> str:
    config_root = Path(CONFIG_ROOT).expanduser().resolve()
    dotfiles_root = Path(DOTFILES_ROOT).expanduser().resolve()
    resolved_path = path.expanduser().resolve(strict=False)
    if resolved_path == config_root:
        return "CONFIG_ROOT"
    if resolved_path.is_relative_to(config_root):
        relative_path = resolved_path.relative_to(config_root)
        return f"CONFIG_ROOT/{relative_path.as_posix()}"
    if resolved_path == dotfiles_root:
        return "DOTFILES_ROOT"
    if resolved_path.is_relative_to(dotfiles_root):
        relative_path = resolved_path.relative_to(dotfiles_root)
        return f"DOTFILES_ROOT/{relative_path.as_posix()}"
    return _format_home_relative_path(path)


def _build_entry_name(original_path: Path) -> str:
    return original_path.stem.replace(".", "_").replace("-", "_")


def _build_flat_backup_name(original_path: Path) -> str:
    normalized_path = original_path.expanduser().absolute()
    location = _format_home_relative_path(normalized_path.parent)
    location_hash = hashlib.sha256(location.encode("utf-8")).hexdigest()[:FLAT_PATH_HASH_LENGTH]
    return f"{location_hash}.{normalized_path.name}"


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


def _path_exists_for_register(path: Path) -> bool:
    return path.exists() or path.is_symlink()


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
        case "private" | "v" | "public" | "b":
            pass
        case _:
            raise ValueError(f"Unknown sensitivity: {sensitivity}")
    if destination is None:
        new_path = BACKUP_ROOT_FLAT.joinpath(_build_flat_backup_name(orig_path))
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
        case "private" | "v" | "public" | "b":
            pass
        case _:
            raise ValueError(f"Unknown sensitivity: {sensitivity}")
    if destination is None:
        raise ValueError("Cannot derive the original path from a flat hashed backup path. Use the mapper entry instead.")
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
    on_conflict: Annotated[ON_CONFLICT_LOOSE, typer.Option(..., "--on-conflict", "-c", help="Action to take on conflict")] = "throw-error",
    sensitivity: Annotated[Literal["private", "v", "public", "b"], typer.Option(..., "--sensitivity", "-s", help="Sensitivity of the config file.")] = "private",
    destination: Annotated[str | None, typer.Option("--destination", "-d", help="destination folder (override the default, use at your own risk)")] = None,
    section: Annotated[str, typer.Option("--section", "-se", help="Section name in mapper_dotfiles.yaml to record this mapping.")] = "default",
    os_filter: Annotated[str, typer.Option("--os", help="Comma-separated OS list from: linux,darwin,windows.")] = DEFAULT_OS_FILTER,
    shared: Annotated[bool, typer.Option("--shared", "-sh", help="Whether the config file is shared across destinations directory.")] = False,
    record: Annotated[bool, typer.Option("--record", "-r", help="Record the mapping in user's mapper.yaml")] = True,
    ) -> None:
    from rich.console import Console
    from rich.panel import Panel
    from stackops.utils.links import symlink_map, copy_map
    console = Console()
    orig_path = Path(file).expanduser().absolute()
    new_path = get_backup_path(orig_path=orig_path, sensitivity=sensitivity, destination=destination, shared=shared)
    if not _path_exists_for_register(orig_path) and not _path_exists_for_register(new_path):
        console.print(f"[red]Error:[/] Neither original file nor self-managed file exists:\n  Original: {orig_path}\n  Self-managed: {new_path}")
        raise typer.Exit(code=1)
    new_path.parent.mkdir(parents=True, exist_ok=True)
    match method:
        case "copy" | "c":
            try:
                result = copy_map(
                    config_file_default_path=orig_path,
                    config_file_self_managed_path=new_path,
                    on_conflict=ON_CONFLICT_MAPPER[on_conflict],
                )
            except Exception as e:
                msg = typer.style("Error: ", fg=typer.colors.RED) + str(e)
                typer.echo(msg)
                raise typer.Exit(code=1) from e
        case "symlink" | "s":
            try:
                result = symlink_map(
                    config_file_default_path=orig_path,
                    config_file_self_managed_path=new_path,
                    on_conflict=ON_CONFLICT_MAPPER[on_conflict],
                )
            except Exception as e:
                msg = typer.style("Error: ", fg=typer.colors.RED) + str(e)
                typer.echo(msg)
                raise typer.Exit(code=1) from e
        case _:
            raise ValueError(f"Unknown method: {method}")
    if result["action"] == "error":
        raise typer.Exit(code=1)
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
    from stackops.profile.create_links_export import REPO_MAP

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
        ) -> None:
    """🔗 Export dotfiles for migration to new machine."""
    if over_internet and over_ssh:
        print("❌ Choose only one transfer mode: --over-internet or --over-ssh.")
        raise typer.Exit(code=1)
    if over_internet:
        print("❌ Internet-based transfer is not yet implemented.")
        raise typer.Exit(code=1)

    dotfiles_dir = DOTFILES_ROOT
    if not dotfiles_dir.exists() or not dotfiles_dir.is_dir():
        print(f"❌ Dotfiles directory does not exist: {dotfiles_dir}")
        raise typer.Exit(code=1)
    dotfiles_zip = DOTFILES_ZIP_PATH
    if dotfiles_zip.exists():
        dotfiles_zip.unlink()
    zipfile = shutil.make_archive(base_name=str(dotfiles_zip)[:-4], format="zip", root_dir=str(dotfiles_dir), base_dir=".", verbose=False)
    from stackops.utils.io import encrypt_file_symmetric

    zipfile_path = Path(zipfile)
    zipfile_encrypted_path = encrypt_file_symmetric(file_path=zipfile_path, pwd=pwd)
    zipfile_path.unlink()
    print(f"✅ Dotfiles exported to: {zipfile_encrypted_path}")
    if over_ssh:
        code_sample = f"ftpx {_format_home_relative_path(DOTFILES_ZIP_PATH)}.gpg user@remote_host:^"
        print("🔗 Exporting dotfiles via SSH-based transfer (scp).")
        print(f"💡 Run the following command on your local machine to copy dotfiles to the remote machine:\n{code_sample}")
        remote_address = typer.prompt("Enter the remote machine address (user@host) to copy dotfiles to ")
        code_concrete = f"ftpx {zipfile_encrypted_path} {remote_address}:^"
        from stackops.utils.code import run_shell_script
        run_shell_script(code_concrete, display_script=True, clean_env=False)
        return
    # devops network share-server --no-auth ./dotfiles.zip
    from stackops.scripts.python.helpers.helpers_devops import cli_share_server
    from stackops.scripts.python.helpers.helpers_network.address import select_lan_ipv4

    localipv4 = select_lan_ipv4(prefer_vpn=False)
    if localipv4 is None:
        msg = typer.style("Error: ", fg=typer.colors.RED) + "Could not determine local LAN IPv4 address for dotfiles export."
        typer.echo(msg, err=True)
        raise typer.Exit(code=1)
    port = 8888
    msg = f"""On the remote machine, run the following:
d c i -u http://{localipv4}:{port} -p {pwd}
"""
    from stackops.utils.accessories import display_with_flashy_style

    display_with_flashy_style(msg=msg, title="Remote Machine Instructions")
    cli_share_server.web_file_explorer(
        path=str(zipfile_encrypted_path),
        no_auth=True,
        port=port,
        # bind_address="
    )


def _validate_dotfiles_archive(zip_ref: zipfile.ZipFile, destination: Path) -> None:
    destination_resolved = destination.resolve(strict=False)
    for zip_member in zip_ref.infolist():
        member_path = Path(zip_member.filename)
        if zip_member.filename == "" or member_path.is_absolute() or ".." in member_path.parts:
            raise ValueError(f"Unsafe path in dotfiles archive: {zip_member.filename}")
        extracted_path = destination.joinpath(zip_member.filename).resolve(strict=False)
        if extracted_path != destination_resolved and not extracted_path.is_relative_to(destination_resolved):
            raise ValueError(f"Unsafe path in dotfiles archive: {zip_member.filename}")

    corrupt_member = zip_ref.testzip()
    if corrupt_member is not None:
        raise ValueError(f"Corrupt file in dotfiles archive: {corrupt_member}")


def _resolve_import_dotfiles_source(url: str) -> Path:
    from urllib.parse import urlparse

    parsed_url = urlparse(url)
    if parsed_url.scheme in {"", "file"}:
        local_path_text = url if parsed_url.scheme == "" else parsed_url.path
        local_path = Path(local_path_text).expanduser()
        if not local_path.exists():
            raise FileNotFoundError(f"Encrypted dotfiles archive not found: {local_path}")
        if not local_path.is_file():
            raise IsADirectoryError(f"Expected an encrypted dotfiles archive file, got: {local_path}")
        return local_path.resolve()

    from stackops.scripts.python.helpers.helpers_utils.download import download

    downloaded_file = download(url=url, decompress=False, output_dir=str(Path.home()))
    if downloaded_file is None or not downloaded_file.exists():
        raise FileNotFoundError(f"Failed to download encrypted dotfiles archive from: {url}")
    return downloaded_file


def import_dotfiles(
        url: Annotated[str | None, typer.Option(..., "--url", "-u", help="URL or local path to the encrypted dotfiles archive (.zip.gpg)")] = None,
        pwd: Annotated[str | None, typer.Option(..., "--pwd", "-p", help="Password for zip decryption")] = None,
        use_ssh: Annotated[bool, typer.Option("--use-ssh", "-s", help="Use SSH-based transfer (scp) from a remote machine that has dotfiles.")]=False,
        ) -> None:
    # # INSECURE cd $HOME; uvx wormhole-magic receive dotfiles.zip.gpg --accept-file
    # ☁️  [bold blue]Method 3: USING INTERNET SECURE SHARE[/bold blue]
    #     [dim]cd ~
    #     cloud copy SHARE_URL . --config ss[/dim]
    if use_ssh:
        print("🔗 Importing dotfiles via SSH-based transfer (scp).")
        dotfiles_display_path = _format_home_relative_path(DOTFILES_ROOT)
        code = f"""cloud ftpx $USER@$(hostname):^ {dotfiles_display_path} -z"""
        print(f"💡 Run the following command on the remote machine that has the dotfiles:\n{code}")
        url = typer.prompt("Enter the remote machine address (user@host) to copy dotfiles from ")

        code_concrete = f"cloud ftpx {url}:^ {dotfiles_display_path} -z"
        from stackops.utils.code import run_shell_script
        run_shell_script(code_concrete, display_script=True, clean_env=False)

        print("✅ Dotfiles copied via SSH.")
        return
    if url is None:
        url = typer.prompt(f"Enter the URL or local path to the encrypted dotfiles zip (e.g. http://192.168.20.4:8888 or {_format_home_relative_path(DOTFILES_ZIP_PATH)}.gpg) ")
    if pwd is None:
        pwd = typer.prompt("Enter the password for zip decryption", hide_input=True)
    assert url is not None, "URL prompt should have produced an archive location."
    try:
        zipfile_encrypted_path = _resolve_import_dotfiles_source(url=url)
    except (FileNotFoundError, IsADirectoryError) as error:
        msg = typer.style("Error: ", fg=typer.colors.RED) + str(error)
        typer.echo(msg)
        raise typer.Exit(code=1) from error
    from stackops.utils.io import GpgCommandError, decrypt_file_symmetric

    assert pwd is not None, "Password prompt should have produced a decryption password."
    try:
        zipfile_path = decrypt_file_symmetric(file_path=zipfile_encrypted_path, pwd=pwd)
    except (FileNotFoundError, IsADirectoryError, RuntimeError, GpgCommandError) as error:
        msg = typer.style("Error: ", fg=typer.colors.RED) + str(error)
        typer.echo(msg)
        raise typer.Exit(code=1) from error
    print(f"✅ Decrypted zip file saved to: {zipfile_path}")
    dotfiles_path = DOTFILES_ROOT
    try:
        with tempfile.TemporaryDirectory(prefix=".stackops-dotfiles-import-", dir=dotfiles_path.parent) as temp_dir:
            extracted_dotfiles_path = Path(temp_dir).joinpath("dotfiles")
            extracted_dotfiles_path.mkdir()
            with zipfile.ZipFile(zipfile_path, "r") as zip_ref:
                _validate_dotfiles_archive(zip_ref=zip_ref, destination=extracted_dotfiles_path)
                zip_ref.extractall(extracted_dotfiles_path)
            if dotfiles_path.exists():
                if not dotfiles_path.is_dir() or dotfiles_path.is_symlink():
                    msg = typer.style("Error: ", fg=typer.colors.RED) + f"Refusing to overwrite non-directory path: {dotfiles_path}"
                    typer.echo(msg)
                    raise typer.Exit(code=1)
                print(f"⚠️  WARNING: Overwriting existing directory: {dotfiles_path}")
                shutil.rmtree(dotfiles_path)
            shutil.move(str(extracted_dotfiles_path), str(dotfiles_path))
    except (zipfile.BadZipFile, ValueError) as error:
        msg = typer.style("Error: ", fg=typer.colors.RED) + str(error)
        typer.echo(msg)
        raise typer.Exit(code=1) from error
    finally:
        if zipfile_path.exists():
            zipfile_path.unlink()
    print(f"✅ Dotfiles extracted to: {dotfiles_path}")


def arg_parser() -> None:
    typer.run(register_dotfile)


if __name__ == "__main__":
    arg_parser()
