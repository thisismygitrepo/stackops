from typing import Any, Callable, Protocol, TYPE_CHECKING
from pathlib import Path
from stackops.utils.cli_utils.terminal import Response
from stackops.utils.machine.specs import MachineSpecs

if TYPE_CHECKING:
    import paramiko


STACKOPS_VERSION = "26.6.5"
STACKOPS_REQUIREMENT = f"stackops>={STACKOPS_VERSION}"
DEFAULT_PICKLE_SUBDIR = "tmp_results/tmp_scripts/ssh"


class SSHConnection(Protocol):
    sftp: "paramiko.SFTPClient | None"
    hostname: str
    remote_specs: MachineSpecs
    tqdm_wrap: Callable[..., Any]

    def create_parent_dir_and_check_if_exists(self, path_rel2home: str, overwrite_existing: bool) -> None: ...
    def copy_from_here(self, source_path: str, target_rel2home: str | None, compress_with_zip: bool, recursive: bool, overwrite_existing: bool) -> None: ...
    def copy_to_here(self, source: str | Path, target: str | Path | None, compress_with_zip: bool, recursive: bool, internal_call: bool) -> None: ...
    def run_shell_cmd_on_remote(self, command: str, verbose_output: bool, description: str, strict_stderr: bool, strict_return_code: bool) -> Response: ...
    def run_py_remotely(self, python_code: str, uv_with: list[str] | None, uv_project_dir: str | None, description: str, verbose_output: bool, strict_stderr: bool, strict_return_code: bool) -> Response: ...
    def simple_sftp_get(self, remote_path: str, local_path: Path) -> None: ...
    def expand_remote_path(self, source_path: str | Path) -> str: ...
    def check_remote_is_dir(self, source_path: str | Path) -> bool: ...
