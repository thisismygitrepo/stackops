import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath


def upload_workspace(
    *, executable: str, name: str, snapshot: Path, inputs: tuple[Path, ...], command: list[str], staging: Path,
) -> tuple[PurePosixPath, list[str]]:
    execution = [executable, "sandbox", "exec", "--name", name, "--no-tty", "--no-login-shell"]
    completed = subprocess.run(
        [*execution, "--", "sh", "-c", "pwd -P"],
        stdin=subprocess.DEVNULL, capture_output=True, text=True, check=True,
    )
    root = PurePosixPath(completed.stdout.rstrip("\n"))
    if not root.is_absolute():
        raise ValueError("OpenShell did not return an absolute sandbox working directory.")
    project = root / snapshot.name
    subprocess.run(
        [*execution, "--", "sh", "-c", 'test ! -e "$1" && test ! -L "$1"', "sh", str(project)],
        stdin=subprocess.DEVNULL, stdout=sys.stderr, check=True,
    )
    subprocess.run(
        [executable, "sandbox", "upload", "--no-git-ignore", name, str(snapshot), str(root)],
        stdin=subprocess.DEVNULL, stdout=sys.stderr, check=True,
    )
    subprocess.run(
        [
            *execution, "--workdir", str(project), "--", "sh", "-c",
            "git init -q && git add --all --force && git -c user.name=stackops -c user.email=stackops@localhost "
            "-c commit.gpgsign=false commit -q --allow-empty -m 'Workspace snapshot'",
        ],
        stdin=subprocess.DEVNULL, stdout=sys.stderr, check=True,
    )
    mapped: dict[str, str] = {}
    for index, source in enumerate(inputs):
        destination = staging / f"""input-{index}"""
        destination.mkdir()
        target = destination / source.name
        if source.is_dir():
            shutil.copytree(source, target, symlinks=True)
        else:
            shutil.copy2(source, target)
        remote = root / destination.name / source.name
        subprocess.run(
            [executable, "sandbox", "upload", "--no-git-ignore", name, str(destination), str(root)],
            stdin=subprocess.DEVNULL, stdout=sys.stderr, check=True,
        )
        mapped[str(source)] = str(remote)
    return project, [mapped.get(argument, argument) for argument in command]
