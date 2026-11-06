from pathlib import Path
from typing import Annotated, cast
import zipfile
import typer

from stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_mapper import format_home_relative_path
from stackops.utils.cli_utils.interaction import require_interactive
from stackops.utils.cli_utils.secret_input import read_secret_input


def export_dotfiles(
    ssh: Annotated[bool, typer.Option("--ssh", "-s", help="Use SSH-based transfer (scp) to a remote machine")] = False,
    remote: Annotated[str | None, typer.Option("--remote", "-r", help="SSH destination user@host; requires --ssh.")] = None,
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Destination for the encrypted .zip.gpg archive.")] = None,
    password_file: Annotated[Path | None, typer.Option("--password-file", "-F", help="Read password from a file, or - for stdin.")] = None,
    password_env: Annotated[str | None, typer.Option("--password-env", "-E", help="Read password from this environment variable name.")] = None,
    serve: Annotated[bool, typer.Option("--serve", "-S", help="Serve the encrypted archive until interrupted.")] = False,
) -> None:
    """Export dotfiles for migration to new machine."""
    import shutil

    from stackops.utils.source_of_truth import DOTFILES_ROOT, DOTFILES_ZIP_PATH

    if remote is not None and not ssh:
        raise typer.BadParameter("--remote requires --ssh.")
    if serve and ssh:
        raise typer.BadParameter("--serve and --ssh cannot be combined.")
    if ssh and remote is None:
        require_interactive("Choose SSH destination; supply --remote USER@HOST")
        remote = cast(str, typer.prompt("Remote destination (user@host)"))
    output_path = output.expanduser().absolute() if output is not None else None
    if output_path is not None and output_path.exists():
        raise typer.BadParameter(f"Output already exists: {output_path}")
    pwd = read_secret_input(value=None, file=password_file, env=password_env, prompt="Password for zip encryption")
    if not DOTFILES_ROOT.exists() or not DOTFILES_ROOT.is_dir():
        print(f"Dotfiles directory does not exist: {DOTFILES_ROOT}")
        raise typer.Exit(code=1)
    if DOTFILES_ZIP_PATH.exists():
        DOTFILES_ZIP_PATH.unlink()
    archive_path = shutil.make_archive(base_name=str(DOTFILES_ZIP_PATH)[:-4], format="zip", root_dir=str(DOTFILES_ROOT), base_dir=".", verbose=False)

    from stackops.utils.io import encrypt_file_symmetric
    zipfile_path = Path(archive_path)
    zipfile_encrypted_path = encrypt_file_symmetric(file_path=zipfile_path, pwd=pwd)
    zipfile_path.unlink()
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(zipfile_encrypted_path), str(output_path))
        zipfile_encrypted_path = output_path
    print(f"Dotfiles exported to: {zipfile_encrypted_path}")

    if ssh:
        import subprocess

        result = subprocess.run(["cloud", "transfer", str(zipfile_encrypted_path), f"{remote}:^"], check=False)
        if result.returncode != 0:
            raise typer.Exit(code=result.returncode)
        return
    if not serve:
        return

    from stackops.scripts.python.helpers.helpers_devops import cli_share_server
    from stackops.utils.accessories import display_with_flashy_style
    from stackops.utils.network.address import select_lan_ipv4

    local_ipv4 = select_lan_ipv4(prefer_vpn=False)
    if local_ipv4 is None:
        msg = typer.style("Error: ", fg=typer.colors.RED) + "Could not determine local LAN IPv4 address for dotfiles export."
        typer.echo(msg, err=True)
        raise typer.Exit(code=1)
    port = 8888
    display_with_flashy_style(msg=f"""
On the remote machine, run:
d c f i -u http://{local_ipv4}:{port} && d c f s d -s user -m s -w all
devops config dotfiles import --url http://{local_ipv4}:{port} && devops config dotfiles sync down --source user --method symlink --which all
""", title="Remote Machine Instructions")
    cli_share_server.web_file_explorer(path=str(zipfile_encrypted_path), no_auth=True, port=port)


def _validate_dotfiles_archive(zip_ref: "zipfile.ZipFile", destination: Path) -> None:
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
    url: Annotated[str | None, typer.Option(..., "--url", "-u", help="URL or local path to the encrypted dotfiles archive (.zip.gpg)")] = None,
    ssh: Annotated[bool, typer.Option("--ssh", "-s", help="Use SSH-based transfer (scp) from a remote machine that has dotfiles.")] = False,
    remote: Annotated[str | None, typer.Option("--remote", "-r", help="SSH source user@host; requires --ssh.")] = None,
    password_file: Annotated[Path | None, typer.Option("--password-file", "-F", help="Read password from a file, or - for stdin.")] = None,
    password_env: Annotated[str | None, typer.Option("--password-env", "-E", help="Read password from this environment variable name.")] = None,
) -> None:
    import shutil
    import tempfile

    from stackops.utils.source_of_truth import DOTFILES_ROOT, DOTFILES_ZIP_PATH

    if remote is not None and not ssh:
        raise typer.BadParameter("--remote requires --ssh.")
    if ssh:
        import subprocess

        if url is not None or password_file is not None or password_env is not None:
            raise typer.BadParameter("SSH import uses --remote; --url and archive password inputs do not apply.")
        if remote is None:
            require_interactive("Choose SSH source; supply --remote USER@HOST")
            remote = cast(str, typer.prompt("Remote source (user@host)"))
        result = subprocess.run(["cloud", "transfer", f"{remote}:^", str(DOTFILES_ROOT), "-z"], check=False)
        if result.returncode != 0:
            raise typer.Exit(code=result.returncode)
        print("Dotfiles copied via SSH.")
        return

    if url is None:
        require_interactive("Choose an encrypted archive; supply --url URL_OR_PATH")
        url = cast(str, typer.prompt(f"""Enter the URL or local path to the encrypted dotfiles zip (e.g. http://192.168.20.4:8888 or {format_home_relative_path(DOTFILES_ZIP_PATH)}.gpg) """))
    pwd = read_secret_input(value=None, file=password_file, env=password_env, prompt="Password for zip decryption")
    assert url is not None
    try:
        zipfile_encrypted_path = _resolve_import_dotfiles_source(url=url)
    except (FileNotFoundError, IsADirectoryError) as error:
        msg = typer.style("Error: ", fg=typer.colors.RED) + str(error)
        typer.echo(msg)
        raise typer.Exit(code=1) from error

    from stackops.utils.io import GpgCommandError, decrypt_file_symmetric
    try:
        zipfile_path = decrypt_file_symmetric(file_path=zipfile_encrypted_path, pwd=pwd)
    except (FileNotFoundError, IsADirectoryError, RuntimeError, GpgCommandError) as error:
        msg = typer.style("Error: ", fg=typer.colors.RED) + str(error)
        typer.echo(msg)
        raise typer.Exit(code=1) from error
    print(f"Decrypted zip file saved to: {zipfile_path}")
    try:
        with tempfile.TemporaryDirectory(prefix=".stackops-dotfiles-import-", dir=DOTFILES_ROOT.parent) as temp_dir:
            extracted_path = Path(temp_dir).joinpath("dotfiles")
            extracted_path.mkdir()
            with zipfile.ZipFile(zipfile_path, "r") as zip_ref:
                _validate_dotfiles_archive(zip_ref=zip_ref, destination=extracted_path)
                zip_ref.extractall(extracted_path)
            if DOTFILES_ROOT.exists():
                if not DOTFILES_ROOT.is_dir() or DOTFILES_ROOT.is_symlink():
                    msg = typer.style("Error: ", fg=typer.colors.RED) + f"Refusing to overwrite non-directory path: {DOTFILES_ROOT}"
                    typer.echo(msg)
                    raise typer.Exit(code=1)
                print(f"WARNING: Overwriting existing directory: {DOTFILES_ROOT}")
                shutil.rmtree(DOTFILES_ROOT)
            shutil.move(str(extracted_path), str(DOTFILES_ROOT))
    except (zipfile.BadZipFile, ValueError) as error:
        msg = typer.style("Error: ", fg=typer.colors.RED) + str(error)
        typer.echo(msg)
        raise typer.Exit(code=1) from error
    finally:
        if zipfile_path.exists():
            zipfile_path.unlink()
    print(f"Dotfiles extracted to: {DOTFILES_ROOT}")
