"""Dotfile archive transfer commands."""

from pathlib import Path
import shutil
import tempfile
from typing import Annotated
import zipfile

import typer


def _format_home_relative_path(path: Path) -> str:
    home = Path.home()
    if path.is_relative_to(home):
        return f"~/{path.relative_to(home).as_posix()}"
    return path.as_posix()


def export_dotfiles(
    pwd: Annotated[str, typer.Argument(..., help="Password for zip encryption")],
    over_internet: Annotated[
        bool,
        typer.Option("--over-internet", "-i", help="Use internet-based transfer (wormhole-magic)"),
    ] = False,
    over_ssh: Annotated[
        bool,
        typer.Option("--over-ssh", "-s", help="Use SSH-based transfer (scp) to a remote machine"),
    ] = False,
) -> None:
    """🔗 Export dotfiles for migration to new machine."""
    if over_internet and over_ssh:
        print("❌ Choose only one transfer mode: --over-internet or --over-ssh.")
        raise typer.Exit(code=1)
    if over_internet:
        print("❌ Internet-based transfer is not yet implemented.")
        raise typer.Exit(code=1)

    from stackops.utils.source_of_truth import DOTFILES_ROOT, DOTFILES_ZIP_PATH

    dotfiles_dir = DOTFILES_ROOT
    if not dotfiles_dir.exists() or not dotfiles_dir.is_dir():
        print(f"❌ Dotfiles directory does not exist: {dotfiles_dir}")
        raise typer.Exit(code=1)

    dotfiles_zip = DOTFILES_ZIP_PATH
    if dotfiles_zip.exists():
        dotfiles_zip.unlink()
    archive_path = shutil.make_archive(
        base_name=str(dotfiles_zip)[:-4],
        format="zip",
        root_dir=str(dotfiles_dir),
        base_dir=".",
        verbose=False,
    )

    from stackops.utils.io import encrypt_file_symmetric

    zipfile_path = Path(archive_path)
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

    from stackops.scripts.python.helpers.helpers_devops import cli_share_server
    from stackops.utils.network.address import select_lan_ipv4

    local_ipv4 = select_lan_ipv4(prefer_vpn=False)
    if local_ipv4 is None:
        msg = typer.style("Error: ", fg=typer.colors.RED) + "Could not determine local LAN IPv4 address for dotfiles export."
        typer.echo(msg, err=True)
        raise typer.Exit(code=1)

    port = 8888
    msg = f"""On the remote machine, run the following:
d c I -u http://{local_ipv4}:{port} -p {pwd}
"""

    from stackops.utils.accessories import display_with_flashy_style

    display_with_flashy_style(msg=msg, title="Remote Machine Instructions")
    cli_share_server.web_file_explorer(
        path=str(zipfile_encrypted_path),
        no_auth=True,
        port=port,
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

    from stackops.utils.files.download import download

    downloaded_file = download(url=url, decompress=False, output_dir=str(Path.home()))
    if downloaded_file is None or not downloaded_file.exists():
        raise FileNotFoundError(f"Failed to download encrypted dotfiles archive from: {url}")
    return downloaded_file


def import_dotfiles(
    url: Annotated[
        str | None,
        typer.Option(..., "--url", "-u", help="URL or local path to the encrypted dotfiles archive (.zip.gpg)"),
    ] = None,
    pwd: Annotated[
        str | None,
        typer.Option(..., "--pwd", "-p", help="Password for zip decryption"),
    ] = None,
    use_ssh: Annotated[
        bool,
        typer.Option("--use-ssh", "-s", help="Use SSH-based transfer (scp) from a remote machine that has dotfiles."),
    ] = False,
) -> None:
    from stackops.utils.source_of_truth import DOTFILES_ROOT, DOTFILES_ZIP_PATH

    if use_ssh:
        print("🔗 Importing dotfiles via SSH-based transfer (scp).")
        dotfiles_display_path = _format_home_relative_path(DOTFILES_ROOT)
        code = f"cloud ftpx $USER@$(hostname):^ {dotfiles_display_path} -z"
        print(f"💡 Run the following command on the remote machine that has the dotfiles:\n{code}")
        url = typer.prompt("Enter the remote machine address (user@host) to copy dotfiles from ")

        code_concrete = f"cloud ftpx {url}:^ {dotfiles_display_path} -z"

        from stackops.utils.code import run_shell_script

        run_shell_script(code_concrete, display_script=True, clean_env=False)
        print("✅ Dotfiles copied via SSH.")
        return

    if url is None:
        url = typer.prompt(
            "Enter the URL or local path to the encrypted dotfiles zip "
            f"(e.g. http://192.168.20.4:8888 or {_format_home_relative_path(DOTFILES_ZIP_PATH)}.gpg) "
        )
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
