from pathlib import Path
import platform
import tempfile

from rich.console import Console
from rich.panel import Panel


def get_tmux_cmd(wd1: Path, wd2: Path) -> str:
    lines = [
        f"""tmux new-session -d -s gitdiff -c {wd1}""",
        """tmux send-keys -t gitdiff 'git status' C-m""",
        f"""tmux split-window -h -t gitdiff -c {wd2}""",
        """tmux send-keys -t gitdiff 'git status' C-m""",
        """tmux attach-session -t gitdiff""",
    ]
    return "\n".join(lines)


def _quote_powershell_literal(value: Path) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def get_windows_inspect_cmd(wd1: Path, wd2: Path) -> str:
    local_path = _quote_powershell_literal(value=wd1)
    remote_path = _quote_powershell_literal(value=wd2)
    return f'mprocs "git -C {local_path} status" "git -C {remote_path} status" --names "local,integration"'


def inspect_repos(repo_local_root: str, repo_remote_root: str) -> None:
    console = Console()
    console.print(
        Panel(
            f"📂 Local:       {repo_local_root}\n📂 Integration: {repo_remote_root}",
            title="[bold blue]🔍 Inspecting Repositories[/bold blue]",
            border_style="blue",
        )
    )
    if platform.system() == "Windows":
        program = get_windows_inspect_cmd(wd1=Path(repo_local_root), wd2=Path(repo_remote_root))
        suffix = ".ps1"
    elif platform.system() in ["Linux", "Darwin"]:
        program = get_tmux_cmd(wd1=Path(repo_local_root), wd2=Path(repo_remote_root))
        suffix = ".sh"
    else:
        raise NotImplementedError(f"Platform {platform.system()} not implemented.")
    with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False, encoding="utf-8") as temp_file:
        temp_file.write(program)
        temp_script_path = Path(temp_file.name)
    console.print(Panel(f"Run the inspection script:\n\n[blue]{temp_script_path}[/blue]", border_style="blue"))
