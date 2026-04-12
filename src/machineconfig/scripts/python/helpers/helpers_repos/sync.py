from machineconfig.utils.path_extended import PathExtended
from machineconfig.utils.io import encrypt_file_asymmetric
from machineconfig.utils.path_core import delete_path
from machineconfig.utils.rclone_wrapper import get_remote_path, to_cloud
import platform
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

console = Console()


def get_zellij_cmd(wd1: Path, wd2: Path) -> str:
    _ = wd1, wd2
    lines = [
        """ zellij action new-tab --name gitdiff""",
        """zellij action new-pane --direction down --name local --cwd ./data """,
        """zellij action write-chars "cd '{wd1}'; git status" """,
        """zellij action move-focus up; zellij action close-pane """,
        """zellij action new-pane --direction down --name remote --cwd code """,
        """zellij action write-chars "cd '{wd2}' """,
        """git status" """,
    ]
    return "; ".join(lines)

def delete_remote_repo_copy_and_push_local(remote_repo: str, local_repo: str, cloud: str):
    console.print(Panel("🗑️  Deleting remote repo copy and pushing local copy", title="[bold blue]Repo Sync[/bold blue]", border_style="blue"))
    repo_sync_root = PathExtended(remote_repo).expanduser().absolute()
    repo_root_path = PathExtended(local_repo).expanduser().absolute()
    delete_path(repo_sync_root, verbose=True)
    print("🧹 Removed temporary remote copy")
    from git.remote import Remote
    from git.repo import Repo

    try:
        Remote.remove(Repo(repo_root_path), "originEnc")
        console.print(Panel("🔗 Removed originEnc remote reference", border_style="blue"))
    except Exception:
        pass
    console.print(Panel("📈 Deleting remote repository copy and pushing local changes", width=150, border_style="blue"))
    archive_path = Path(PathExtended(repo_root_path).zip(inplace=False))
    encrypted_archive_path = encrypt_file_asymmetric(file_path=archive_path)
    remote_path = Path(f"{get_remote_path(local_path=repo_root_path, root='myhome', os_specific=False, rel2home=True, strict=True).as_posix()}.zip.gpg")
    try:
        to_cloud(
            local_path=encrypted_archive_path,
            cloud=cloud,
            remote_path=remote_path,
            share=False,
            verbose=True,
            transfers=10,
        )
    finally:
        delete_path(archive_path, verbose=False)
        delete_path(encrypted_archive_path, verbose=False)

    console.print(Panel("✅ Repository successfully pushed to cloud", title="[bold green]Repo Sync[/bold green]", border_style="green"))



def get_wt_cmd(wd1: PathExtended, wd2: PathExtended) -> str:
    lines = [
        f"""wt --window 0 new-tab --profile pwsh --title "gitdiff" --tabColor `#3b04d1 --startingDirectory {wd1} ` --colorScheme "Solarized Dark" """,
        f"""split-pane --horizontal --profile pwsh --startingDirectory {wd2} --size 0.5 --colorScheme "Tango Dark" -- pwsh -Interactive """,
    ]
    return " `; ".join(lines)


def inspect_repos(repo_local_root: str, repo_remote_root: str):
    console.print(Panel(f"📂 Local:  {repo_local_root}\n📂 Remote: {repo_remote_root}", title="[bold blue]🔍 Inspecting Repositories[/bold blue]", border_style="blue"))

    if platform.system() == "Windows":
        program = get_wt_cmd(wd1=PathExtended(repo_local_root), wd2=PathExtended(repo_local_root))
    elif platform.system() in ["Linux", "Darwin"]:
        program = get_zellij_cmd(wd1=PathExtended(repo_local_root), wd2=PathExtended(repo_remote_root))
    else:
        raise NotImplementedError(f"Platform {platform.system()} not implemented.")
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix=".sh" if platform.system() != "Windows" else ".ps1", delete=False, encoding='utf-8') as temp_file:
        temp_file.write(program)
        temp_script_path = PathExtended(temp_file.name)
    console.print(Panel(f"🚀 Launching repo inspection tool...\n\n[blue]{temp_script_path}[/blue]", border_style="blue"))
