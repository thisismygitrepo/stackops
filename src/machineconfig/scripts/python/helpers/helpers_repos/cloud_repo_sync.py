

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

from machineconfig.utils.io import (
    decrypt_file_asymmetric,
    decrypt_file_symmetric,
    encrypt_file_asymmetric,
    encrypt_file_symmetric,
)
from machineconfig.utils.path_extended import PathExtended
from machineconfig.utils.rclone import RcloneCommandError, is_missing_remote_path_error
import machineconfig.utils.rclone_wrapper as rclone_wrapper
from machineconfig.utils.ssh_utils.abc import MACHINECONFIG_VERSION


REMOTE_NAME = "originEnc"
REMOTE_BRANCH_NAME = "master"


@dataclass(frozen=True)
class MergeAttemptResult:
    status: Literal["success", "merge_conflict", "git_error"]
    details: str
    conflict_paths: tuple[str, ...]


def get_tmp_file() -> Path:
    import platform
    from machineconfig.utils.accessories import randstr

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
    try:
        commit_output = repo.git.commit(m=message)
        if commit_output.strip() != "":
            print(commit_output)
    except GitCommandError as exc:
        print(exc)
        print("-> Commit skipped/failed (continuing).")


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
        PathExtended(temp_path).delete(sure=True, verbose=False)


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
    archive_path = Path(PathExtended(repo_root).zip(inplace=False))
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
    PathExtended(encrypted_archive_path).delete(sure=True, verbose=False)
    return Path(PathExtended(archive_path).unzip(inplace=True, verbose=True, overwrite=True, content=True, merge=False))


def _merge_remote_copy(repo: Repo, remote_path: PathExtended, console: Console) -> MergeAttemptResult:
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
    repo: Annotated[str, typer.Argument(..., help="Path to the local repository. Defaults to current working directory.")],
    cloud: Annotated[str | None, typer.Option(..., "--cloud", "-c", help="Cloud storage profile name. If not provided, uses default from config.")] = None,
    message: Annotated[str | None, typer.Option(..., "--message", "-m", help="Commit message for local changes.")] = None,
    on_conflict: Annotated[Literal["ask", "a",
                                   "push-local-merge", "p",
                                   "overwrite-local", "o",
                                   "stop-on-conflict", "s",
                                   "remove-rclone-conflict", "r"
                                    ], typer.Option(..., "--on-conflict", "-o", help="Action to take on merge conflict. Default is 'ask'.")] = "ask",
    pwd: Annotated[str | None, typer.Option(..., "--password", help="Password for encryption/decryption of the remote repository.")] = None,
) -> str | None:
    on_conflict_mapper: dict[str, Literal["ask", "push-local-merge", "overwrite-local", "stop-on-conflict", "remove-rclone-conflict"]] = {
        "a": "ask",
        "ask": "ask",
        "p": "push-local-merge",
        "push-local-merge": "push-local-merge",
        "o": "overwrite-local",
        "overwrite-local": "overwrite-local",
        "s": "stop-on-conflict",
        "stop-on-conflict": "stop-on-conflict",
        "r": "remove-rclone-conflict",
        "remove-rclone-conflict": "remove-rclone-conflict",
    }
    on_conflict = on_conflict_mapper[on_conflict]
    import platform

    from machineconfig.utils.source_of_truth import CONFIG_ROOT, DEFAULTS_PATH
    from machineconfig.utils.code import get_uv_command_executing_python_script
    console = Console()

    def _ps_single_quote(val: str) -> str:
        return "'" + val.replace("'", "''") + "'"

    if cloud is None:
        try:
            from machineconfig.utils.io import read_ini
            cloud_resolved = read_ini(DEFAULTS_PATH)["general"]["rclone_config_name"]
            console.print(Panel(f"⚠️  Using default cloud: `{cloud_resolved}` from {DEFAULTS_PATH}", title="Default Cloud", border_style="yellow"))
        except FileNotFoundError:
            console.print(Panel(f"❌ ERROR: No cloud profile found\nLocation: {DEFAULTS_PATH}\nPlease set one up or provide one via the --cloud flag.", title="Error", border_style="red"))
            return ""
    else:
        cloud_resolved = cloud
    repo_local_root = PathExtended.cwd() if repo == "." else PathExtended(repo).expanduser().absolute()
    try:
        repo_local_obj = Repo(repo_local_root, search_parent_directories=True)
    except (InvalidGitRepositoryError, NoSuchPathError) as exc:
        msg = typer.style("Error: ", fg=typer.colors.RED) + f"The specified path '{repo_local_root}' is not a valid git repository."
        typer.echo(msg)
        raise typer.Exit(code=1) from exc
    repo_local_root = PathExtended(repo_local_obj.working_dir)  # cwd might have been in a sub directory of repo_root, so its better to redefine it.
    local_relative_home = PathExtended(repo_local_root.expanduser().absolute().relative_to(Path.home()))
    PathExtended(CONFIG_ROOT).joinpath("remote").mkdir(parents=True, exist_ok=True)
    repo_remote_root = PathExtended(CONFIG_ROOT).joinpath("remote", local_relative_home)
    repo_remote_root.delete(sure=True)
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

    _commit_local_changes(repo=repo_local_obj, message=message_resolved, console=console)
    merge_result = _merge_remote_copy(repo=repo_local_obj, remote_path=repo_remote_root, console=console)

    if Path.home().joinpath("code/machineconfig").exists():
        uv_project_dir = f"""{str(Path.home().joinpath("code/machineconfig"))}"""
        uv_with = None
    else:
        uv_with = [MACHINECONFIG_VERSION]
        uv_project_dir = None

    if merge_result.status == "success":
        console.print(Panel("✅ Pull succeeded!\n🧹 Removing originEnc remote and local copy\n📤 Pushing merged repository to cloud storage", title="Success", border_style="green"))
        repo_remote_root.delete(sure=True)
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
        return "error"
    conflict_paths_text = "\n".join(f"• {path}" for path in merge_result.conflict_paths)
    conflict_details = f"\n\nConflicting paths:\n{conflict_paths_text}" if conflict_paths_text != "" else ""
    console.print(Panel(f"⚠️  MERGE FAILED\n💾 Keeping local copy of remote at:\n📂 {repo_remote_root}{conflict_details}", title="Merge Failed", border_style="red"))

    # ================================================================================
    option1 = "Delete remote copy and push local:"
    from machineconfig.utils.meta import lambda_to_python_script

    def func2(remote_repo: str, local_repo: str, cloud: str) -> None:
        from machineconfig.scripts.python.helpers.helpers_repos.sync import delete_remote_repo_copy_and_push_local

        delete_remote_repo_copy_and_push_local(remote_repo=remote_repo, local_repo=local_repo, cloud=cloud)

    program_1_py = lambda_to_python_script(lambda: func2(remote_repo=str(repo_remote_root), local_repo=str(repo_local_root), cloud=str(cloud_resolved)),
                                                    in_global=True, import_module=False)
    program1, _pyfile1 = get_uv_command_executing_python_script(python_script=program_1_py, uv_with=uv_with, uv_project_dir=uv_project_dir)
    # ================================================================================

    option2 = "Delete local repo and replace it with remote copy:"
    if platform.system() == "Windows":
        program_2 = f"""
Remove-Item -LiteralPath {_ps_single_quote(repo_local_root_str)} -Recurse -Force -ErrorAction SilentlyContinue
Move-Item -LiteralPath {_ps_single_quote(repo_remote_root_str)} -Destination {_ps_single_quote(repo_local_root_str)} -Force
    """
    else:
        program_2 = f"""
rm -rfd {_bash_quote(repo_local_root_str)}
mv {_bash_quote(repo_remote_root_str)} {_bash_quote(repo_local_root_str)}
    """
    if platform.system() in ["Linux", "Darwin"]:
        program_2 += """
sudo chmod 600 $HOME/.ssh/*
sudo chmod 700 $HOME/.ssh
sudo chmod +x $HOME/dotfiles/scripts/linux -R
"""
    shell_file_2 = get_tmp_file()
    shell_file_2.write_text(program_2, encoding="utf-8")

    # ================================================================================
    option3 = "Inspect repos:"

    def func(repo_local_root: str, repo_remote_root: str) -> None:
        from machineconfig.scripts.python.helpers.helpers_repos.sync import inspect_repos

        inspect_repos(repo_local_root=repo_local_root, repo_remote_root=repo_remote_root)

    program_3_py = lambda_to_python_script(lambda: func(repo_local_root=str(repo_local_root), repo_remote_root=str(repo_remote_root)),
                                                    in_global=True, import_module=False)
    program3, _pyfile3 = get_uv_command_executing_python_script(python_script=program_3_py, uv_with=uv_with, uv_project_dir=uv_project_dir)
    # ================================================================================

    option4 = "Remove problematic rclone file from repo and replace with remote:"
    if platform.system() == "Windows":
        program_4 = f"""
Remove-Item -LiteralPath "$HOME/dotfiles/creds/rclone/rclone.conf" -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path "$HOME/dotfiles/creds/rclone" -Force | Out-Null
Copy-Item -LiteralPath "$HOME/.config/machineconfig/remote/dotfiles/creds/rclone/rclone.conf" -Destination "$HOME/dotfiles/creds/rclone/rclone.conf" -Force
Set-Location -LiteralPath "$HOME/dotfiles"
git commit -am "finished merging"
{program1}
    """
    else:
        program_4 = f"""
rm $HOME/dotfiles/creds/rclone/rclone.conf
cp $HOME/.config/machineconfig/remote/dotfiles/creds/rclone/rclone.conf $HOME/dotfiles/creds/rclone
cd $HOME/dotfiles
git commit -am "finished merging"
{program1}
    """
    shell_file_4 = get_tmp_file()
    shell_file_4.write_text(program_4, encoding="utf-8")
    # ================================================================================

    console.print(Panel("🔄 RESOLVE MERGE CONFLICT\nChoose an option to resolve the conflict:", title_align="left", border_style="blue"))

    print(f"• {option1:75} 👉 {program1}")
    print(f"• {option2:75} 👉 {shell_file_2}")
    print(f"• {option3:75} 👉 {program3}")
    print(f"• {option4:75} 👉 {shell_file_4}")
    print("\n\n")

    program_content = None
    match on_conflict:
        case "ask":
            import questionary
            choice = questionary.select("Choose one option:", choices=[option1, option2, option3, option4]).ask()
            if choice == option1:
                program_content = program1
            elif choice == option2:
                program_content = program_2
            elif choice == option3:
                program_content = program3
            elif choice == option4:
                program_content = program_4
            else:
                raise NotImplementedError(f"Choice {choice} not implemented.")
        case "push-local-merge":
            program_content = program1
        case "overwrite-local":
            program_content = program_2
        case "stop-on-conflict":
            program_content = program3
        case "remove-rclone-conflict":
            program_content = program_4
        case _:
            raise ValueError(f"Unknown action: {on_conflict}")
    from machineconfig.utils.code import run_shell_script
    run_shell_script(script=program_content, display_script=True, clean_env=False)
    return program_content
