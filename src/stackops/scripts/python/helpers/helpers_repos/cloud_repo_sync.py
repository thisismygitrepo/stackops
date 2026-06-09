

from dataclasses import dataclass
from pathlib import Path
import shlex
from typing import Annotated, Literal

from git.exc import GitCommandError, InvalidGitRepositoryError, NoSuchPathError
from git.remote import Remote
from git.repo import Repo
from rich.console import Console
from rich.panel import Panel
import typer

from stackops.utils.io import (
    decrypt_file_asymmetric,
    decrypt_file_symmetric,
    encrypt_file_asymmetric,
    encrypt_file_symmetric,
)
from stackops.utils.path_core import delete_path
import stackops.utils.path_compression as path_compression
from stackops.utils.rclone import RcloneCommandError, is_missing_remote_path_error
import stackops.utils.rclone_wrapper as rclone_wrapper
from stackops.utils.ssh_utils.abc import STACKOPS_REQUIREMENT
from stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_conflicts import (
    ConflictResolutionOption,
    build_merge_accept_program,
    powershell_single_quote,
    resolve_conflict_action,
)


REMOTE_NAME = "originEnc"
REMOTE_BRANCH_NAME = "master"


@dataclass(frozen=True)
class MergeAttemptResult:
    status: Literal["success", "merge_conflict", "git_error"]
    details: str
    conflict_paths: tuple[str, ...]


def get_tmp_file() -> Path:
    import platform
    from stackops.utils.accessories import randstr

    name = randstr(8)
    if platform.system() == "Windows":
        suffix = "ps1"
    else:
        suffix = "sh"
    tmp_file = Path.home().joinpath(f"tmp_results/tmp_files/{name}.{suffix}")
    tmp_file.parent.mkdir(parents=True, exist_ok=True)
    return tmp_file


def _print_section(console: Console, title: str) -> None:
    console.print("")
    console.print(f"[bold blue]═════ {title} ═════[/bold blue]")


def _bash_quote(value: str) -> str:
    return shlex.quote(value)


def _has_staged_changes(repo: Repo) -> bool:
    if repo.head.is_valid():
        return len(repo.index.diff("HEAD")) > 0
    return repo.git.diff("--cached", "--name-only").strip() != ""


def _commit_local_changes(repo: Repo, message: str, console: Console) -> None:
    _print_section(console=console, title="COMMITTING LOCAL CHANGES")
    print(repo.git.status())
    repo.git.add(A=True)
    if not _has_staged_changes(repo=repo):
        print("-> No staged changes to commit.")
        return
    commit_output = repo.git.commit(m=message)
    if commit_output.strip() != "":
        print(commit_output)


def _find_remote(repo: Repo, remote_name: str) -> Remote | None:
    for remote in repo.remotes:
        if remote.name == remote_name:
            return remote
    return None


def _remove_remote_if_present(repo: Repo, remote_name: str) -> None:
    remote = _find_remote(repo=repo, remote_name=remote_name)
    if remote is not None:
        Remote.remove(repo, remote_name)


def _get_remote_reference_name(remote: Remote, branch_name: str) -> str:
    for reference in remote.refs:
        if reference.remote_head == branch_name:
            return reference.name
    raise RuntimeError(f"Remote branch '{branch_name}' was not fetched from '{remote.name}'.")


def _get_conflict_paths(repo: Repo) -> tuple[str, ...]:
    return tuple(sorted(str(path) for path in repo.index.unmerged_blobs().keys()))


def _cleanup_temp_paths(paths: tuple[Path, ...]) -> None:
    for temp_path in paths:
        delete_path(temp_path, verbose=False)


def _get_repo_remote_archive_path(repo_root: Path) -> Path:
    base_remote_path = rclone_wrapper.get_remote_path(
        local_path=repo_root,
        root="myhome",
        os_specific=False,
        rel2home=True,
        strict=True,
    )
    return Path(f"{base_remote_path.as_posix()}.zip.gpg")


def _upload_repo_archive(repo_root: Path, cloud: str, remote_path: Path, pwd: str | None) -> None:
    archive_path = path_compression.zip_path(
        repo_root,
        path=None,
        folder=None,
        name=None,
        arcname=None,
        inplace=False,
        verbose=True,
        content=False,
        orig=False,
        mode="w",
    )
    if pwd is None:
        encrypted_archive_path = encrypt_file_asymmetric(file_path=archive_path)
    else:
        encrypted_archive_path = encrypt_file_symmetric(file_path=archive_path, pwd=pwd)
    try:
        rclone_wrapper.to_cloud(
            local_path=encrypted_archive_path,
            cloud=cloud,
            remote_path=remote_path,
            share=False,
            verbose=True,
            transfers=10,
        )
    finally:
        _cleanup_temp_paths((archive_path, encrypted_archive_path))


def _download_repo_archive(repo_remote_root: Path, cloud: str, remote_path: Path, pwd: str | None) -> Path:
    encrypted_archive_path = Path(f"{repo_remote_root}.zip.gpg")
    rclone_wrapper.from_cloud(
        local_path=encrypted_archive_path,
        cloud=cloud,
        remote_path=remote_path,
        transfers=10,
        verbose=True,
    )
    if pwd is None:
        archive_path = decrypt_file_asymmetric(file_path=encrypted_archive_path)
    else:
        archive_path = decrypt_file_symmetric(file_path=encrypted_archive_path, pwd=pwd)
    delete_path(encrypted_archive_path, verbose=False)
    return path_compression.unzip_path(
        archive_path,
        folder=None,
        path=None,
        name=None,
        verbose=True,
        content=True,
        inplace=True,
        overwrite=True,
        orig=False,
        pwd=None,
        tmp=False,
        pattern=None,
        merge=False,
    )


def _merge_remote_copy(repo: Repo, remote_path: Path, console: Console) -> MergeAttemptResult:
    _print_section(console=console, title="PULLING LATEST FROM REMOTE")
    print(f"-> Trying to removing {REMOTE_NAME} remote from local repo if it exists.")
    _remove_remote_if_present(repo=repo, remote_name=REMOTE_NAME)
    print(f"-> Adding {REMOTE_NAME} remote to local repo")
    remote = repo.create_remote(REMOTE_NAME, str(remote_path))
    try:
        print(f"-> Fetching {REMOTE_NAME} remote.")
        remote.fetch(REMOTE_BRANCH_NAME)
        remote_reference_name = _get_remote_reference_name(remote=remote, branch_name=REMOTE_BRANCH_NAME)
        merge_output = repo.git.merge(remote_reference_name, no_edit=True)
    except GitCommandError as exc:
        conflict_paths = _get_conflict_paths(repo=repo)
        if len(conflict_paths) > 0:
            return MergeAttemptResult(status="merge_conflict", details=str(exc), conflict_paths=conflict_paths)
        return MergeAttemptResult(status="git_error", details=str(exc), conflict_paths=())
    conflict_paths = _get_conflict_paths(repo=repo)
    if len(conflict_paths) > 0:
        return MergeAttemptResult(
            status="merge_conflict",
            details="Merge finished but the repository still contains unresolved paths.",
            conflict_paths=conflict_paths,
        )
    return MergeAttemptResult(status="success", details=merge_output, conflict_paths=())


def main(
    repo: Annotated[str, typer.Argument(help="Path to the local repository. Defaults to current working directory.")] = ".",
    cloud: Annotated[str | None, typer.Option(..., "--cloud", "-C", help="Cloud storage profile name. If not provided, uses default from config.")] = None,
    message: Annotated[str | None, typer.Option(..., "--message", "-m", help="Commit message for local changes.")] = None,
    on_conflict: Annotated[ConflictResolutionOption, typer.Option(..., "--on-conflict", "-c", help="Action to take on merge conflict. Default is 'ask'.")] = "ask",
    pwd: Annotated[str | None, typer.Option(..., "--password", help="Password for encryption/decryption of the remote repository.")] = None,
) -> str | None:
    on_conflict = resolve_conflict_action(on_conflict=on_conflict)
    import platform

    from stackops.utils.source_of_truth import CONFIG_ROOT, DOTFILES_RCLONE_CONF_PATH, DOTFILES_ROOT, DOTFILES_SCRIPTS_ROOT, DOTFILES_STACKOPS_CONFIG_PATH, read_stackops_config_string
    from stackops.utils.code import get_uv_command_executing_python_script
    console = Console()

    if cloud is None:
        try:
            cloud_resolved = read_stackops_config_string("default_rclone_config")
            console.print(Panel(f"⚠️  Using default cloud: `{cloud_resolved}` from {DOTFILES_STACKOPS_CONFIG_PATH}", title="Default Cloud", border_style="yellow"))
        except (FileNotFoundError, KeyError, ValueError) as exc:
            console.print(Panel(f"❌ ERROR: No cloud profile found\nLocation: {DOTFILES_STACKOPS_CONFIG_PATH}\nPlease set one up or provide one via the --cloud flag.", title="Error", border_style="red"))
            raise typer.Exit(code=1) from exc
    else:
        cloud_resolved = cloud
    repo_local_root = Path.cwd() if repo == "." else Path(repo).expanduser().absolute()
    try:
        repo_local_obj = Repo(repo_local_root, search_parent_directories=True)
    except (InvalidGitRepositoryError, NoSuchPathError) as exc:
        msg = typer.style("Error: ", fg=typer.colors.RED) + f"The specified path '{repo_local_root}' is not a valid git repository."
        typer.echo(msg)
        raise typer.Exit(code=1) from exc
    repo_local_root = Path(repo_local_obj.working_dir)  # cwd might have been in a sub directory of repo_root, so its better to redefine it.
    try:
        local_relative_home = repo_local_root.expanduser().absolute().relative_to(Path.home())
    except ValueError as exc:
        console.print(
            Panel(
                f"❌ ERROR: Repository must live under {Path.home()}\nLocation: {repo_local_root}",
                title="Error",
                border_style="red",
            )
        )
        raise typer.Exit(code=1) from exc
    Path(CONFIG_ROOT).joinpath("remote").mkdir(parents=True, exist_ok=True)
    repo_remote_root = Path(CONFIG_ROOT).joinpath("remote", local_relative_home)
    delete_path(repo_remote_root, verbose=True)
    remote_path = _get_repo_remote_archive_path(repo_root=repo_local_root)
    try:
        console.print(Panel("📥 DOWNLOADING REMOTE REPOSITORY", title_align="left", border_style="blue"))
        _download_repo_archive(repo_remote_root=repo_remote_root, cloud=cloud_resolved, remote_path=remote_path, pwd=pwd)
    except RcloneCommandError as error:
        if not is_missing_remote_path_error(error):
            raise
        console.print(Panel("🆕 Remote repository doesn't exist\n📤 Creating new remote and exiting...", title_align="left", border_style="green"))
        _upload_repo_archive(repo_root=repo_local_root, cloud=cloud_resolved, remote_path=remote_path, pwd=pwd)
        return ""

    repo_remote_obj = Repo(repo_remote_root)
    if repo_remote_obj.is_dirty():
        console.print(Panel(f"⚠️  WARNING: REMOTE REPOSITORY IS DIRTY\nLocation: {repo_remote_root}\nPlease commit or stash changes before proceeding.", title="Warning", border_style="yellow"))

    message_resolved = "sync" if message is None or message.strip() == "" else message

    repo_local_root_str = str(repo_local_root)
    repo_remote_root_str = str(repo_remote_root)

    try:
        _commit_local_changes(repo=repo_local_obj, message=message_resolved, console=console)
    except GitCommandError as exc:
        console.print(
            Panel(
                f"❌ COMMIT FAILED\n{exc}",
                title="Commit Failed",
                border_style="red",
            )
        )
        raise typer.Exit(code=1) from exc
    merge_result = _merge_remote_copy(repo=repo_local_obj, remote_path=repo_remote_root, console=console)

    if Path.home().joinpath("code/stackops").exists():
        uv_project_dir = f"""{str(Path.home().joinpath("code/stackops"))}"""
        uv_with = None
    else:
        uv_with = [STACKOPS_REQUIREMENT]
        uv_project_dir = None

    if merge_result.status == "success":
        console.print(Panel("✅ Pull succeeded!\n🧹 Removing originEnc remote and local copy\n📤 Pushing merged repository to cloud storage", title="Success", border_style="green"))
        delete_path(repo_remote_root, verbose=True)
        _remove_remote_if_present(repo=repo_local_obj, remote_name=REMOTE_NAME)
        _upload_repo_archive(repo_root=repo_local_root, cloud=cloud_resolved, remote_path=remote_path, pwd=pwd)
        return "success"
    if merge_result.status == "git_error":
        console.print(
            Panel(
                f"❌ PULL FAILED\n💾 Keeping local copy of remote at:\n📂 {repo_remote_root}\n\n{merge_result.details}",
                title="Pull Failed",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)
    conflict_paths_text = "\n".join(f"• {path}" for path in merge_result.conflict_paths)
    conflict_details = f"\n\nConflicting paths:\n{conflict_paths_text}" if conflict_paths_text != "" else ""
    console.print(Panel(f"⚠️  MERGE FAILED\n💾 Keeping local copy of remote at:\n📂 {repo_remote_root}{conflict_details}", title="Merge Failed", border_style="red"))

    # ================================================================================
    option1 = "Delete remote copy and push local:"
    from stackops.utils.meta import lambda_to_python_script

    def func2(remote_repo: str, local_repo: str, cloud: str) -> None:
        from stackops.scripts.python.helpers.helpers_repos.sync import delete_remote_repo_copy_and_push_local

        delete_remote_repo_copy_and_push_local(remote_repo=remote_repo, local_repo=local_repo, cloud=cloud)

    program_1_py = lambda_to_python_script(lambda: func2(remote_repo=str(repo_remote_root), local_repo=str(repo_local_root), cloud=str(cloud_resolved)),
                                                    in_global=True, import_module=False)
    program1, _pyfile1 = get_uv_command_executing_python_script(python_script=program_1_py, uv_with=uv_with, uv_project_dir=uv_project_dir)
    # ================================================================================

    option2 = "Delete local repo and replace it with remote copy:"
    if platform.system() == "Windows":
        program_2 = f"""
Remove-Item -LiteralPath {powershell_single_quote(repo_local_root_str)} -Recurse -Force -ErrorAction SilentlyContinue
Move-Item -LiteralPath {powershell_single_quote(repo_remote_root_str)} -Destination {powershell_single_quote(repo_local_root_str)} -Force
    """
    else:
        program_2 = f"""
rm -rfd {_bash_quote(repo_local_root_str)}
mv {_bash_quote(repo_remote_root_str)} {_bash_quote(repo_local_root_str)}
    """
    if platform.system() in ["Linux", "Darwin"]:
        dotfiles_linux_scripts = DOTFILES_SCRIPTS_ROOT / "linux"
        program_2 += f"""
sudo chmod 600 $HOME/.ssh/*
sudo chmod 700 $HOME/.ssh
sudo chmod +x {_bash_quote(str(dotfiles_linux_scripts))} -R
"""
    shell_file_2 = get_tmp_file()
    shell_file_2.write_text(program_2, encoding="utf-8")

    # ================================================================================
    option3 = "Inspect repos:"

    def func(repo_local_root: str, repo_remote_root: str) -> None:
        from stackops.scripts.python.helpers.helpers_repos.sync import inspect_repos

        inspect_repos(repo_local_root=repo_local_root, repo_remote_root=repo_remote_root)

    program_3_py = lambda_to_python_script(lambda: func(repo_local_root=str(repo_local_root), repo_remote_root=str(repo_remote_root)),
                                                    in_global=True, import_module=False)
    program3, _pyfile3 = get_uv_command_executing_python_script(python_script=program_3_py, uv_with=uv_with, uv_project_dir=uv_project_dir)
    # ================================================================================

    option4 = "Remove problematic rclone file from repo and replace with remote:"
    remote_dotfiles_rclone_conf = CONFIG_ROOT.joinpath("remote", "dotfiles", "creds", "rclone", "rclone.conf")
    if platform.system() == "Windows":
        program_4 = f"""
Remove-Item -LiteralPath {powershell_single_quote(str(DOTFILES_RCLONE_CONF_PATH))} -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path {powershell_single_quote(str(DOTFILES_RCLONE_CONF_PATH.parent))} -Force | Out-Null
Copy-Item -LiteralPath {powershell_single_quote(str(remote_dotfiles_rclone_conf))} -Destination {powershell_single_quote(str(DOTFILES_RCLONE_CONF_PATH))} -Force
Set-Location -LiteralPath {powershell_single_quote(str(DOTFILES_ROOT))}
git commit -am "finished merging"
{program1}
    """
    else:
        program_4 = f"""
rm {_bash_quote(str(DOTFILES_RCLONE_CONF_PATH))}
cp {_bash_quote(str(remote_dotfiles_rclone_conf))} {_bash_quote(str(DOTFILES_RCLONE_CONF_PATH.parent))}
cd {_bash_quote(str(DOTFILES_ROOT))}
git commit -am "finished merging"
{program1}
    """
    shell_file_4 = get_tmp_file()
    shell_file_4.write_text(program_4, encoding="utf-8")
    # ================================================================================

    option5 = "Finish merge and accept remote only for conflicting files:"
    program_5 = build_merge_accept_program(
        repo_local_root=repo_local_root,
        conflict_paths=merge_result.conflict_paths,
        accept_side="remote",
        push_local_program=program1,
        platform_name=platform.system(),
    )
    shell_file_5 = get_tmp_file()
    shell_file_5.write_text(program_5, encoding="utf-8")

    option6 = "Finish merge and accept local only for conflicting files:"
    program_6 = build_merge_accept_program(
        repo_local_root=repo_local_root,
        conflict_paths=merge_result.conflict_paths,
        accept_side="local",
        push_local_program=program1,
        platform_name=platform.system(),
    )
    shell_file_6 = get_tmp_file()
    shell_file_6.write_text(program_6, encoding="utf-8")
    # ================================================================================

    console.print(Panel("🔄 RESOLVE MERGE CONFLICT\nChoose an option to resolve the conflict:", title_align="left", border_style="blue"))

    print(f"• {option1:75} 👉 {program1}")
    print(f"• {option2:75} 👉 {shell_file_2}")
    print(f"• {option3:75} 👉 {program3}")
    print(f"• {option4:75} 👉 {shell_file_4}")
    print(f"• {option5:75} 👉 {shell_file_5}")
    print(f"• {option6:75} 👉 {shell_file_6}")
    print("\n\n")

    if on_conflict == "stop-on-conflict":
        raise typer.Exit(code=1)

    program_content = None
    match on_conflict:
        case "ask":
            import questionary
            choice = questionary.select("Choose one option:", choices=[option1, option2, option3, option4, option5, option6]).ask()
            if choice is None:
                raise typer.Exit(code=1)
            if choice == option1:
                program_content = program1
            elif choice == option2:
                program_content = program_2
            elif choice == option3:
                program_content = program3
            elif choice == option4:
                program_content = program_4
            elif choice == option5:
                program_content = program_5
            elif choice == option6:
                program_content = program_6
            else:
                raise NotImplementedError(f"Choice {choice} not implemented.")
        case "push-local-merge":
            program_content = program1
        case "overwrite-local":
            program_content = program_2
        case "merge-accept-remote":
            program_content = program_5
        case "merge-accept-local":
            program_content = program_6
        case "remove-rclone-conflict":
            program_content = program_4
        case _:
            raise ValueError(f"Unknown action: {on_conflict}")
    from stackops.utils.code import run_shell_script
    run_shell_script(script=program_content, display_script=True, clean_env=False)
    return program_content
