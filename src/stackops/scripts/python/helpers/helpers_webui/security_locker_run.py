import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypedDict, cast

from stackops.scripts.python.helpers.helpers_devops.cli_data_encrypt import FolderArchiveFormat
from stackops.scripts.python.helpers.helpers_webui.runs import build_run_environment
from stackops.scripts.python.helpers.helpers_webui.security_constants import FOLDER_MEASURE_LIMIT, LOCKER_DETAIL_LIMIT, LOCKER_SECRET_MASK
from stackops.scripts.python.helpers.helpers_webui.security_locker_look import COMPRESSIONS, LockerMode, look_at
from stackops.scripts.python.helpers.helpers_webui.security_paths import PathMeasure, measure_path, resolve_typed_path

type LockerFailure = Literal["wrong_password", "needs_key", "exists", "overlap", "failed"]
DEVOPS_MODULE = "stackops.scripts.python.devops"


@dataclass(frozen=True)
class LockerRefusal:
    message: str


@dataclass(frozen=True)
class PasswordRun:
    mode: LockerMode
    source: Path
    password: str
    compression: FolderArchiveFormat
    output: Path | None
    overwrite: bool


class LockerOutcome(TypedDict):
    failure: LockerFailure | None
    detail: str
    result: PathMeasure | None


def parse_password_run(body: object) -> PasswordRun | LockerRefusal:
    if not isinstance(body, dict):
        return LockerRefusal(message="Expected a JSON object.")
    payload = cast(dict[str, object], body)
    mode, path, base, password = payload.get("mode"), payload.get("path"), payload.get("base"), payload.get("password")
    compression, output, overwrite = payload.get("compression"), payload.get("output"), payload.get("overwrite")
    if mode not in ("encrypt", "decrypt") or not isinstance(path, str) or path.strip() == "" or not isinstance(base, str):
        return LockerRefusal(message="Say whether to encrypt or decrypt, and which file.")
    if not isinstance(password, str) or password == "":
        return LockerRefusal(message="Type a password first.")
    # GPG reads the password as one line, so anything after a line break would be dropped without a word.
    if "\n" in password or "\r" in password:
        return LockerRefusal(message="A password cannot hold a line break.")
    if compression not in COMPRESSIONS or not isinstance(output, str) or not isinstance(overwrite, bool):
        return LockerRefusal(message="The options of this run are not ones the command takes.")
    return PasswordRun(
        mode=mode, source=resolve_typed_path(path, base_directory=base), password=password, compression=compression,
        output=None if output.strip() == "" else resolve_typed_path(output, base_directory=base), overwrite=overwrite,
    )


def _failure_of(text: str) -> LockerFailure:
    said = text.lower()
    if "bad session key" in said or "bad passphrase" in said:
        return "wrong_password"
    if "no secret key" in said:
        return "needs_key"
    if "output path already exists" in said:
        return "exists"
    return "overlap" if "paths overlap" in said else "failed"


# What went wrong, in GPG's own lines when it spoke, else in the command's. The password is taken out in case anything ever echoes it.
def _detail_of(text: str, password: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    spoken = [line for line in lines if line.startswith("gpg:")] or [line.removeprefix("Error:").strip() for line in lines if line.startswith("Error:")] or lines[-1:]
    return " ".join(spoken).replace(password, LOCKER_SECRET_MASK)[:LOCKER_DETAIL_LIMIT]


# Runs the encrypt or decrypt command with a password typed in the page. The password reaches the command on its standard input, the way the
# command offers for exactly this ("read the password from a file, or - for standard input"), and GPG gets it from there the same way. So it is
# in no argument list and no environment that a list of processes could show, in no file, and nothing here writes it to a log.
def run_with_password(run: PasswordRun) -> LockerOutcome:
    looked = look_at(mode=run.mode, source=run.source, compression=run.compression, output=run.output, secret_ids=frozenset())
    command = [sys.executable, "-m", DEVOPS_MODULE, "data", run.mode, str(run.source), "--encryption", "symmetric", "--password-file", "-"]
    if run.mode == "encrypt":
        command.extend(["--compression", run.compression])
    if run.output is not None:
        command.extend(["--output", str(run.output)])
    if run.overwrite:
        command.append("--overwrite")
    environment = {**build_run_environment(interactive=False), "NO_COLOR": "1", "PYTHONUTF8": "1"}
    completed = subprocess.run(command, input=run.password.encode(encoding="utf-8"), capture_output=True, check=False, env=environment, cwd=str(Path.home()))
    if completed.returncode != 0:
        said = (completed.stdout + b"\n" + completed.stderr).decode(encoding="utf-8", errors="replace")
        return {"failure": _failure_of(said), "detail": _detail_of(said, password=run.password), "result": None}
    return {"failure": None, "detail": "", "result": measure_path(Path(looked["output"]), limit=FOLDER_MEASURE_LIMIT)}
