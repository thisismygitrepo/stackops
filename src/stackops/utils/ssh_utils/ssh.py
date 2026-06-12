from typing import Callable, Any, cast, Union, Literal
import subprocess
from pathlib import Path, PurePosixPath, PureWindowsPath
import platform
from stackops.utils.machine.specs import MachineSpecs
from stackops.utils.code import get_uv_command
import rich.console
from stackops.utils.cli_utils.terminal import Response
from stackops.utils.accessories import pprint, randstr
from stackops.utils.meta import lambda_to_python_script
from stackops.utils.ssh_utils.abc import DEFAULT_PICKLE_SUBDIR, STACKOPS_REQUIREMENT


class SSH:
    @staticmethod
    def _callable_name(func: Callable[..., Any]) -> str:
        func_name = getattr(func, "__name__", None)
        if isinstance(func_name, str):
            return func_name
        return func.__class__.__name__

    @staticmethod
    def from_config_file(host: str) -> "SSH":
        return SSH(host=host, username=None, hostname=None, ssh_key_path=None, password=None, port=22, enable_compression=False)

    def __init__(
        self,
        host: str | None,
        username: str | None,
        hostname: str | None,
        ssh_key_path: str | None,
        password: str | None,
        port: int,
        enable_compression: bool,
    ):
        self.password = password
        self.enable_compression = enable_compression

        self.host: str | None = None
        self.hostname: str
        self.username: str
        self.port: int = port
        self.proxycommand: str | None = None
        import paramiko
        import getpass
        if isinstance(host, str):
            try:
                import paramiko.config as pconfig

                config = pconfig.SSHConfig.from_path(str(Path.home().joinpath(".ssh/config")))
                config_dict = config.lookup(host)
                self.hostname = config_dict["hostname"]
                self.username = config_dict["user"]
                self.host = host
                self.port = int(config_dict.get("port", port))
                identity_file_value = config_dict.get("identityfile", ssh_key_path)
                if isinstance(identity_file_value, list):
                    ssh_key_path = identity_file_value[0]
                else:
                    ssh_key_path = identity_file_value
                self.proxycommand = config_dict.get("proxycommand", None)
                if ssh_key_path is not None:
                    wildcard_identity_file = config.lookup("*").get("identityfile", ssh_key_path)
                    if isinstance(wildcard_identity_file, list):
                        ssh_key_path = wildcard_identity_file[0]
                    else:
                        ssh_key_path = wildcard_identity_file
            except (FileNotFoundError, KeyError):
                assert "@" in host or ":" in host, (
                    f"Host must be in the form of `username@hostname:port` or `username@hostname` or `hostname:port`, but it is: {host}"
                )
                if "@" in host:
                    self.username, self.hostname = host.split("@")
                else:
                    self.username = username or getpass.getuser()
                    self.hostname = host
                if ":" in self.hostname:
                    self.hostname, port_ = self.hostname.split(":")
                    self.port = int(port_)
        elif username is not None and hostname is not None:
            self.username, self.hostname = username, hostname
            self.proxycommand = None
        else:
            print(f"Provided values: host={host}, username={username}, hostname={hostname}")
            raise ValueError("Either host or username and hostname must be provided.")

        self.ssh_key_path = str(Path(ssh_key_path).expanduser().absolute()) if ssh_key_path is not None else None
        self.ssh = paramiko.SSHClient()
        self.ssh.load_system_host_keys()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        pprint(
            dict(host=self.host, hostname=self.hostname, username=self.username, password="***", port=self.port, key_filename=self.ssh_key_path, proxycommand=self.proxycommand),
            title="SSHing To",
        )
        sock = paramiko.ProxyCommand(self.proxycommand) if self.proxycommand is not None else None
        try:
            if password is None:
                allow_agent = True
                look_for_keys = True
            else:
                allow_agent = False
                look_for_keys = False
            self.ssh.connect(
                hostname=self.hostname,
                username=self.username,
                password=self.password,
                port=self.port,
                key_filename=self.ssh_key_path,
                compress=self.enable_compression,
                sock=sock,
                allow_agent=allow_agent,
                look_for_keys=look_for_keys,
            )
        except Exception as _err:
            console = rich.console.Console()
            console.print_exception(show_locals=False, max_frames=3, width=None, word_wrap=True, suppress=[])

            if "getaddrinfo failed" in str(_err) or "Name or service not known" in str(_err):
                console.print("\n[yellow] Hostname Resolution Failed[/yellow]")
                console.print(f"   Target hostname: [cyan]{self.hostname}[/cyan]")
                if self.host and self.host != self.hostname:
                    console.print(f"   SSH config alias: [cyan]{self.host}[/cyan]")
                console.print("\n[yellow] Troubleshooting tips:[/yellow]")
                console.print(f"   1. Check if hostname resolves: [green]ping {self.hostname}[/green]")
                console.print(f"   2. Check SSH config: [green]cat ~/.ssh/config | grep -A5 '{self.host or self.hostname}'[/green]")
                console.print(f"   3. Add to /etc/hosts: [green]echo '192.168.x.x {self.hostname}' | sudo tee -a /etc/hosts[/green]")
                console.print("   4. Check if machine is online and accessible on network\n")

            import sys

            old_settings = None
            if sys.stdin.isatty() and platform.system() != "Windows":
                try:
                    import termios
                    old_settings = termios.tcgetattr(sys.stdin)
                except (ImportError, OSError):
                    pass
            try:
                self.password = getpass.getpass(f"Enter password for {self.username}@{self.hostname}: ")
                self.ssh.connect(
                    hostname=self.hostname,
                    username=self.username,
                    password=self.password,
                    port=self.port,
                    key_filename=self.ssh_key_path,
                    compress=self.enable_compression,
                    sock=sock,
                    allow_agent=False,
                    look_for_keys=False,
                )
            except Exception:
                if old_settings is not None:
                    import termios
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                if sys.stdin.isatty():
                    sys.stdout.write("\033[?25h")
                    sys.stdout.flush()
                raise
            finally:
                if old_settings is not None:
                    import termios
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                if sys.stdin.isatty():
                    sys.stdout.write("\033[?25h")
                    sys.stdout.write("\033[?1049l")
                    sys.stdout.flush()
        try:
            self.sftp: paramiko.SFTPClient | None = self.ssh.open_sftp()
        except Exception as err:
            self.sftp = None
            print(f"""WARNING: Failed to open SFTP connection to {self.hostname}. Error Details: {err}\nData transfer may be affected!""")
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, FileSizeColumn, TransferSpeedColumn

        class RichProgressWrapper:
            def __init__(self, **kwargs: Any):
                self.kwargs = kwargs
                self.progress: Progress | None = None
                self.task: Any | None = None

            def __enter__(self) -> "RichProgressWrapper":
                self.progress = Progress(
                    SpinnerColumn(), TextColumn("[bold blue]{task.description}"), BarColumn(), FileSizeColumn(), TransferSpeedColumn()
                )
                self.progress.start()
                self.task = self.progress.add_task("Transferring...", total=0)
                return self

            def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
                if self.progress:
                    self.progress.stop()

            def view_bar(self, transferred: int, total: int) -> None:
                if self.progress and self.task is not None:
                    self.progress.update(self.task, completed=transferred, total=total)

        self.tqdm_wrap = RichProgressWrapper
        from stackops.utils.machine.specs import get_machine_specs, MACHINE_SPECS_COMMAND_NAME

        self.local_specs: MachineSpecs = get_machine_specs()
        resp = self.run_shell_cmd_on_remote(
            command=f"""~/.local/bin/utils machine {MACHINE_SPECS_COMMAND_NAME} """,
            verbose_output=False,
            description="Getting remote machine specs",
            strict_stderr=False,
            strict_return_code=False,
        )
        json_str = resp.op
        import ast

        self.remote_specs: MachineSpecs = cast(MachineSpecs, ast.literal_eval(json_str))
        self.terminal_responses: list[Response] = []

        from rich import inspect

        console = rich.console.Console()

        from io import StringIO

        local_buffer = StringIO()
        remote_buffer = StringIO()
        local_console = rich.console.Console(file=local_buffer, width=40)
        remote_console = rich.console.Console(file=remote_buffer, width=40)
        inspect(
            type("LocalInfo", (object,), dict(self.local_specs))(),
            value=False,
            title="SSHing From",
            docs=False,
            dunder=False,
            sort=False,
            console=local_console,
        )
        inspect(
            type("RemoteInfo", (object,), dict(self.remote_specs))(),
            value=False,
            title="SSHing To",
            docs=False,
            dunder=False,
            sort=False,
            console=remote_console,
        )
        local_lines = local_buffer.getvalue().split("\n")
        remote_lines = remote_buffer.getvalue().split("\n")
        max_lines = max(len(local_lines), len(remote_lines))
        for i in range(max_lines):
            left = local_lines[i] if i < len(local_lines) else ""
            right = remote_lines[i] if i < len(remote_lines) else ""
            console.print(f"{left:<50} {right}")

    def __enter__(self) -> "SSH":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def close(self) -> None:
        if self.sftp is not None:
            self.sftp.close()
            self.sftp = None
        self.ssh.close()

    def restart_computer(self) -> Response:
        return self.run_shell_cmd_on_remote(
            command="Restart-Computer -Force" if self.remote_specs["system"] == "Windows" else "sudo reboot",
            verbose_output=True,
            description="",
            strict_stderr=False,
            strict_return_code=False,
        )

    def send_ssh_key(self) -> Response:
        self.copy_from_here(source_path="~/.ssh/id_rsa.pub", target_rel2home=None, compress_with_zip=False, recursive=False, overwrite_existing=False)
        if self.remote_specs["system"] != "Windows":
            raise RuntimeError("send_ssh_key is only supported for Windows remote machines")
        python_code = '''
from pathlib import Path
import subprocess
sshd_dir = Path("C:/ProgramData/ssh")
admin_auth_keys = sshd_dir / "administrators_authorized_keys"
sshd_config = sshd_dir / "sshd_config"
pubkey_path = Path.home() / ".ssh" / "id_rsa.pub"
key_content = pubkey_path.read_text(encoding="utf-8").strip()
if admin_auth_keys.exists():
    existing = admin_auth_keys.read_text(encoding="utf-8")
    if not existing.endswith("\\n"):
        existing += "\\n"
    admin_auth_keys.write_text(existing + key_content + "\\n", encoding="utf-8")
else:
    admin_auth_keys.write_text(key_content + "\\n", encoding="utf-8")
icacls_cmd = f'icacls "{admin_auth_keys}" /inheritance:r /grant "Administrators:F" /grant "SYSTEM:F"'
subprocess.run(icacls_cmd, shell=True, check=True)
if sshd_config.exists():
    config_text = sshd_config.read_text(encoding="utf-8")
    config_text = config_text.replace("#PubkeyAuthentication", "PubkeyAuthentication")
    sshd_config.write_text(config_text, encoding="utf-8")
subprocess.run("Restart-Service sshd -Force", shell=True, check=True)
print("SSH key added successfully")
'''
        return self.run_py_remotely(python_code=python_code, uv_with=None, uv_project_dir=None, description="Adding SSH key to Windows remote", verbose_output=True, strict_stderr=False, strict_return_code=False)

    def get_remote_repr(self, add_machine: bool = False) -> str:
        return f"{self.username}@{self.hostname}:{self.port}" + (
            f" [{self.remote_specs['system']}][{self.remote_specs['distro']}]" if add_machine else ""
        )

    def get_local_repr(self, add_machine: bool = False) -> str:
        import getpass

        return f"{getpass.getuser()}@{platform.node()}" + (f" [{platform.system()}][{self.local_specs['distro']}]" if add_machine else "")

    def get_ssh_conn_str(self, command: str) -> str:
        return (
            "ssh "
            + (f" -i {self.ssh_key_path}" if self.ssh_key_path else "")
            + self.get_remote_repr(add_machine=False).replace(":", " -p ")
            + (f" -t {command} " if command != "" else " ")
        )

    def __repr__(self) -> str:
        return f"local {self.get_local_repr(add_machine=True)} >>> SSH TO >>> remote {self.get_remote_repr(add_machine=True)}"

    def run_shell_cmd_on_local(self, command: str) -> Response:
        print(f"""[LOCAL EXECUTION] Running command on node: {self.local_specs["system"]} Command: {command}""")
        res = Response(cmd=command)
        res.output.returncode = subprocess.run(command, shell=True, check=False).returncode
        return res

    def run_shell_cmd_on_remote(
        self, command: str, verbose_output: bool, description: str, strict_stderr: bool, strict_return_code: bool
    ) -> Response:
        raw = self.ssh.exec_command(command)
        res = Response(stdin=raw[0], stdout=raw[1], stderr=raw[2], cmd=command, desc=description)  # type: ignore
        res.capture()
        stdout_channel = getattr(raw[1], "channel", None)
        if stdout_channel is not None:
            res.output.returncode = stdout_channel.recv_exit_status()
        if verbose_output:
            res.print(capture=False)
        else:
            res.print_if_unsuccessful(
                desc=description, strict_err=strict_stderr, strict_returncode=strict_return_code, assert_success=False
            )
        return res

    def _run_py_prep(self, python_code: str, uv_with: list[str] | None, uv_project_dir: str | None, on: Literal["local", "remote"]) -> str:
        py_path = Path.home().joinpath(f"{DEFAULT_PICKLE_SUBDIR}/runpy_{randstr()}.py")
        py_path.parent.mkdir(parents=True, exist_ok=True)
        py_path.write_text(python_code, encoding="utf-8")
        self.copy_from_here(source_path=str(py_path), target_rel2home=None, compress_with_zip=False, recursive=False, overwrite_existing=False)
        if uv_with is not None and len(uv_with) > 0:
            with_clause = " --with " + '"' + ",".join(uv_with) + '"'
        else:
            with_clause = ""
        if uv_project_dir is not None:
            with_clause += f" --project {uv_project_dir}"
        else:
            with_clause += ""
        match on:
            case "local":
                uv_cmd = get_uv_command(platform=self.local_specs["system"])
                py_rel_path = str(py_path.relative_to(Path.home()))
            case "remote":
                uv_cmd = get_uv_command(platform=self.remote_specs["system"])
                py_rel_path = py_path.relative_to(Path.home()).as_posix()
            case _:
                raise ValueError(f"Invalid value for 'on': {on}. Must be 'local' or 'remote'")
        uv_cmd = f"""{uv_cmd} run {with_clause} python {py_rel_path}"""
        return uv_cmd

    def run_py_remotely(
        self,
        python_code: str,
        uv_with: list[str] | None,
        uv_project_dir: str | None,
        description: str,
        verbose_output: bool,
        strict_stderr: bool,
        strict_return_code: bool,
    ) -> Response:
        uv_cmd = self._run_py_prep(python_code=python_code, uv_with=uv_with, uv_project_dir=uv_project_dir, on="remote")
        return self.run_shell_cmd_on_remote(
            command=uv_cmd,
            verbose_output=verbose_output,
            description=description or f"run_py on {self.get_remote_repr(add_machine=False)}",
            strict_stderr=strict_stderr,
            strict_return_code=strict_return_code,
        )

    def run_lambda_function(self, func: Callable[..., Any], import_module: bool, uv_with: list[str] | None, uv_project_dir: str | None) -> Response:
        command = lambda_to_python_script(func, in_global=True, import_module=import_module)
        uv_cmd = self._run_py_prep(python_code=command, uv_with=uv_with, uv_project_dir=uv_project_dir, on="remote")
        if self.remote_specs["system"] == "Linux":
            uv_cmd_modified = f'bash -l -c "{uv_cmd}"'
        else:
            uv_cmd_modified = uv_cmd
        return self.run_shell_cmd_on_remote(
            command=uv_cmd_modified,
            verbose_output=True,
            description=f"run_py_func {self._callable_name(func)} on {self.get_remote_repr(add_machine=False)}",
            strict_stderr=True,
            strict_return_code=True,
        )

    def simple_sftp_get(self, remote_path: str, local_path: Path) -> None:
        if self.sftp is None:
            raise RuntimeError(f"SFTP connection not available for {self.hostname}")
        local_path.parent.mkdir(parents=True, exist_ok=True)
        self.sftp.get(remotepath=remote_path, localpath=str(local_path))

    def _build_remote_path(self, home_dir: str, rel_path: str) -> str:
        if self.remote_specs["system"] == "Windows":
            return str(PureWindowsPath(home_dir) / rel_path)
        return str(PurePosixPath(home_dir) / PurePosixPath(rel_path.replace("\\", "/")))

    def _normalize_rel_path_for_remote(self, rel_path: str) -> str:
        if self.remote_specs["system"] == "Windows":
            return str(PureWindowsPath(rel_path))
        return rel_path.replace("\\", "/")

    def create_parent_dir_and_check_if_exists(self, path_rel2home: str, overwrite_existing: bool) -> None:
        path_rel2home_normalized = self._normalize_rel_path_for_remote(path_rel2home)

        def create_target_dir(target_rel2home: str, overwrite: bool) -> None:
            from pathlib import Path
            import shutil
            target_path_abs = Path(target_rel2home).expanduser()
            if not target_path_abs.is_absolute():
                target_path_abs = Path.home().joinpath(target_path_abs)
            if overwrite and target_path_abs.exists():
                if str(target_path_abs) == str(Path.home()):
                    raise RuntimeError("Refusing to overwrite home directory!")
                if target_path_abs.is_dir():
                    shutil.rmtree(target_path_abs)
                else:
                    target_path_abs.unlink()
            print(f"Creating directory for path: {target_path_abs}")
            target_path_abs.parent.mkdir(parents=True, exist_ok=True)

        command = lambda_to_python_script(
            lambda: create_target_dir(target_rel2home=path_rel2home_normalized, overwrite=overwrite_existing),
            in_global=True, import_module=False,
        )
        tmp_py_file = Path.home().joinpath(f"{DEFAULT_PICKLE_SUBDIR}/create_target_dir_{randstr()}.py")
        tmp_py_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_py_file.write_text(command, encoding="utf-8")
        assert self.sftp is not None
        tmp_remote_path = ".tmp_pyfile.py"
        remote_tmp_full = self._build_remote_path(self.remote_specs["home_dir"], tmp_remote_path)
        self.sftp.put(localpath=str(tmp_py_file), remotepath=remote_tmp_full)
        resp = self.run_shell_cmd_on_remote(
            command=f"""{get_uv_command(platform=self.remote_specs['system'])} run python {tmp_remote_path}""",
            verbose_output=False,
            description=f"Creating target dir {path_rel2home}",
            strict_stderr=True,
            strict_return_code=True,
        )
        resp.print(desc=f"Created target dir {path_rel2home}")

    def check_remote_is_dir(self, source_path: Union[str, Path]) -> bool:
        def check_is_dir(path_to_check: str, json_output_path: str) -> bool:
            from pathlib import Path
            import json
            is_directory = Path(path_to_check).expanduser().absolute().is_dir()
            json_result_path = Path(json_output_path)
            json_result_path.parent.mkdir(parents=True, exist_ok=True)
            json_result_path.write_text(json.dumps(is_directory, indent=2), encoding="utf-8")
            print(json_result_path.as_posix())
            return is_directory

        remote_json_output = Path.home().joinpath(f"{DEFAULT_PICKLE_SUBDIR}/return_{randstr()}.json").as_posix()
        command = lambda_to_python_script(
            lambda: check_is_dir(path_to_check=str(source_path), json_output_path=remote_json_output),
            in_global=True, import_module=False,
        )
        response = self.run_py_remotely(
            python_code=command,
            uv_with=[STACKOPS_REQUIREMENT],
            uv_project_dir=None,
            description=f"Check if source `{source_path}` is a dir",
            verbose_output=False,
            strict_stderr=False,
            strict_return_code=False,
        )
        remote_json_path = response.op.strip()
        if not remote_json_path:
            raise RuntimeError(f"Failed to check if {source_path} is directory - no response from remote")
        local_json = Path.home().joinpath(f"{DEFAULT_PICKLE_SUBDIR}/local_{randstr()}.json")
        self.simple_sftp_get(remote_path=remote_json_path, local_path=local_json)
        import json
        try:
            result = json.loads(local_json.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError) as err:
            raise RuntimeError(f"Failed to check if {source_path} is directory - invalid JSON response: {err}") from err
        finally:
            if local_json.exists():
                local_json.unlink()
        assert isinstance(result, bool), f"Failed to check if {source_path} is directory"
        return result

    def expand_remote_path(self, source_path: Union[str, Path]) -> str:
        source_text = str(source_path)
        if source_text.startswith("~"):
            rel_path = source_text[1:].lstrip("/\\")
            return self._build_remote_path(self.remote_specs["home_dir"], rel_path)
        if self.remote_specs["system"] == "Windows":
            windows_path = PureWindowsPath(source_text)
            if windows_path.is_absolute():
                return str(windows_path)
            return self._build_remote_path(self.remote_specs["home_dir"], source_text)
        posix_path = source_text.replace("\\", "/")
        if posix_path.startswith("/"):
            return posix_path
        return self._build_remote_path(self.remote_specs["home_dir"], posix_path)

    def copy_from_here(
        self, source_path: str, target_rel2home: str | None, compress_with_zip: bool, recursive: bool, overwrite_existing: bool
    ) -> None:
        if self.sftp is None:
            raise RuntimeError(f"SFTP connection not available for {self.hostname}. Cannot transfer files.")
        sftp = self.sftp
        source_obj = Path(source_path).expanduser().absolute()
        if not source_obj.exists():
            raise RuntimeError(f"SSH Error: source `{source_obj}` does not exist!")
        if target_rel2home is None:
            try:
                target_rel2home = str(source_obj.relative_to(Path.home()))
            except ValueError:
                raise RuntimeError(
                    f"If target is not specified, source must be relative to home directory, but got: {source_obj}"
                )
        if not compress_with_zip and source_obj.is_dir():
            if not recursive:
                raise RuntimeError(
                    f"SSH Error: source `{source_obj}` is a directory! Set `recursive=True` for recursive sending or `compress_with_zip=True` to zip it first."
                )
            file_paths_to_upload: list[Path] = [
                file_path for file_path in source_obj.rglob("*") if file_path.is_file()
            ]
            self.create_parent_dir_and_check_if_exists(
                path_rel2home=target_rel2home, overwrite_existing=overwrite_existing
            )
            for idx, file_path in enumerate(file_paths_to_upload):
                print(f"   {idx + 1:03d}. {file_path}")
            for file_path in file_paths_to_upload:
                remote_file_target = Path(target_rel2home).joinpath(
                    file_path.relative_to(source_obj)
                )
                self.copy_from_here(
                    source_path=str(file_path),
                    target_rel2home=str(remote_file_target),
                    compress_with_zip=False,
                    recursive=False,
                    overwrite_existing=overwrite_existing,
                )
            return None
        if compress_with_zip:
            import shutil
            zip_path = Path(str(source_obj) + "_archive")
            if source_obj.is_dir():
                shutil.make_archive(str(zip_path), "zip", source_obj)
            else:
                shutil.make_archive(str(zip_path), "zip", source_obj.parent, source_obj.name)
            source_obj = Path(str(zip_path) + ".zip")
            if not target_rel2home.endswith(".zip"):
                target_rel2home = target_rel2home + ".zip"
        if Path(target_rel2home).parent.as_posix() not in {"", "."}:
            self.create_parent_dir_and_check_if_exists(
                path_rel2home=target_rel2home, overwrite_existing=overwrite_existing
            )
        remote_target_full = self._build_remote_path(
            self.remote_specs["home_dir"], target_rel2home
        )
        print(f"""[SFTP UPLOAD] Sending file: {repr(source_obj)}  ==>  Remote Path: {remote_target_full}""")
        try:
            with self.tqdm_wrap(ascii=True, unit="b", unit_scale=True) as pbar:
                print(f"Uploading {source_obj} to\n{remote_target_full}")
                sftp.put(
                    localpath=str(source_obj),
                    remotepath=remote_target_full,
                    callback=pbar.view_bar,
                )
        except Exception:
            if compress_with_zip and source_obj.exists() and str(source_obj).endswith("_archive.zip"):
                source_obj.unlink()
            raise
        if compress_with_zip:
            def unzip_archive(zip_file_path: str, overwrite_flag: bool) -> None:
                from pathlib import Path
                import shutil
                import zipfile
                archive_path = Path(zip_file_path).expanduser()
                extraction_directory = archive_path.parent / archive_path.stem
                if overwrite_flag and extraction_directory.exists():
                    shutil.rmtree(extraction_directory)
                with zipfile.ZipFile(archive_path, "r") as archive_handle:
                    archive_handle.extractall(extraction_directory)
                archive_path.unlink()

            remote_zip_path = self._build_remote_path(
                self.remote_specs["home_dir"], target_rel2home
            )
            command = lambda_to_python_script(
                lambda: unzip_archive(zip_file_path=remote_zip_path, overwrite_flag=overwrite_existing),
                in_global=True, import_module=False,
            )
            tmp_py_file = Path.home().joinpath(
                f"{DEFAULT_PICKLE_SUBDIR}/create_target_dir_{randstr()}.py"
            )
            tmp_py_file.parent.mkdir(parents=True, exist_ok=True)
            tmp_py_file.write_text(command, encoding="utf-8")
            remote_tmp_py = tmp_py_file.relative_to(Path.home()).as_posix()
            self.copy_from_here(
                source_path=str(tmp_py_file),
                target_rel2home=None,
                compress_with_zip=False,
                recursive=False,
                overwrite_existing=True,
            )
            self.run_shell_cmd_on_remote(
                command=f"""{get_uv_command(platform=self.remote_specs["system"])} run python {remote_tmp_py}""",
                verbose_output=False,
                description=f"UNZIPPING {target_rel2home}",
                strict_stderr=True,
                strict_return_code=True,
            )
            source_obj.unlink()
            tmp_py_file.unlink(missing_ok=True)
        return None

    def copy_to_here(
        self,
        source: Union[str, Path],
        target: Union[str, Path] | None,
        compress_with_zip: bool,
        recursive: bool,
        internal_call: bool,
    ) -> None:
        if self.sftp is None:
            raise RuntimeError(f"SFTP connection not available for {self.hostname}. Cannot transfer files.")
        sftp = self.sftp
        if not internal_call:
            print(f"SFTP DOWNLOADING FROM `{source}` TO `{target}`")
        source_obj = Path(source)
        expanded_source = self.expand_remote_path(source_path=source_obj)
        if not compress_with_zip:
            is_dir = self.check_remote_is_dir(source_path=expanded_source)
            if is_dir:
                if not recursive:
                    raise RuntimeError(
                        f"SSH Error: source `{source_obj}` is a directory! Set recursive=True for recursive transfer or compress_with_zip=True to zip it."
                    )

                def search_files(directory_path: str, json_output_path: str) -> list[str]:
                    from pathlib import Path
                    import json
                    file_paths_list = [
                        file_path.as_posix() for file_path in Path(directory_path).expanduser().absolute().rglob("*") if file_path.is_file()
                    ]
                    json_result_path = Path(json_output_path)
                    json_result_path.parent.mkdir(parents=True, exist_ok=True)
                    json_result_path.write_text(json.dumps(file_paths_list, indent=2), encoding="utf-8")
                    print(json_result_path.as_posix())
                    return file_paths_list

                remote_json_output = Path.home().joinpath(f"{DEFAULT_PICKLE_SUBDIR}/return_{randstr()}.json").as_posix()
                command = lambda_to_python_script(
                    lambda: search_files(directory_path=expanded_source, json_output_path=remote_json_output),
                    in_global=True, import_module=False,
                )
                response = self.run_py_remotely(
                    python_code=command,
                    uv_with=[STACKOPS_REQUIREMENT],
                    uv_project_dir=None,
                    description="Searching for files in source",
                    verbose_output=False,
                    strict_stderr=False,
                    strict_return_code=False,
                )
                remote_json_path = response.op.strip()
                if not remote_json_path:
                    raise RuntimeError(f"Could not resolve source path {source} - no response from remote")
                local_json = Path.home().joinpath(f"{DEFAULT_PICKLE_SUBDIR}/local_{randstr()}.json")
                self.simple_sftp_get(remote_path=remote_json_path, local_path=local_json)
                import json
                try:
                    source_list_str = json.loads(local_json.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, FileNotFoundError) as err:
                    raise RuntimeError(f"Could not resolve source path {source} - invalid JSON response: {err}") from err
                finally:
                    if local_json.exists():
                        local_json.unlink()
                assert isinstance(source_list_str, list), f"Could not resolve source path {source}"
                file_paths_to_download = [Path(file_path_str) for file_path_str in source_list_str]
                if target is None:
                    def collapse_to_home_dir(absolute_path: str, json_output_path: str) -> str:
                        from pathlib import Path
                        import json
                        source_absolute_path = Path(absolute_path).expanduser().absolute()
                        try:
                            relative_to_home = source_absolute_path.relative_to(Path.home())
                            collapsed_path_posix = (Path("~") / relative_to_home).as_posix()
                            json_result_path = Path(json_output_path)
                            json_result_path.parent.mkdir(parents=True, exist_ok=True)
                            json_result_path.write_text(json.dumps(collapsed_path_posix, indent=2), encoding="utf-8")
                            print(json_result_path.as_posix())
                            return collapsed_path_posix
                        except ValueError:
                            raise RuntimeError(f"Source path must be relative to home directory: {source_absolute_path}")

                    remote_json_output = Path.home().joinpath(f"{DEFAULT_PICKLE_SUBDIR}/return_{randstr()}.json").as_posix()
                    command = lambda_to_python_script(
                        lambda: collapse_to_home_dir(absolute_path=expanded_source, json_output_path=remote_json_output),
                        in_global=True, import_module=False,
                    )
                    response = self.run_py_remotely(
                        python_code=command,
                        uv_with=[STACKOPS_REQUIREMENT],
                        uv_project_dir=None,
                        description="Finding default target via relative source path",
                        verbose_output=False,
                        strict_stderr=False,
                        strict_return_code=False,
                    )
                    remote_json_path_dir = response.op.strip()
                    if not remote_json_path_dir:
                        raise RuntimeError("Could not resolve target path - no response from remote")
                    local_json_dir = Path.home().joinpath(f"{DEFAULT_PICKLE_SUBDIR}/local_{randstr()}.json")
                    self.simple_sftp_get(remote_path=remote_json_path_dir, local_path=local_json_dir)
                    import json
                    try:
                        target_dir_str = json.loads(local_json_dir.read_text(encoding="utf-8"))
                    except (json.JSONDecodeError, FileNotFoundError) as err:
                        raise RuntimeError(f"Could not resolve target path - invalid JSON response: {err}") from err
                    finally:
                        if local_json_dir.exists():
                            local_json_dir.unlink()
                    assert isinstance(target_dir_str, str), "Could not resolve target path"
                    target = Path(target_dir_str)
                target_dir = Path(target).expanduser().absolute()
                for idx, file_path in enumerate(file_paths_to_download):
                    print(f"   {idx + 1:03d}. {file_path}")
                for file_path in file_paths_to_download:
                    local_file_target = target_dir.joinpath(Path(file_path).relative_to(expanded_source))
                    self.copy_to_here(source=file_path, target=local_file_target, compress_with_zip=False, recursive=False, internal_call=True)
                return None
        if compress_with_zip:

            def zip_source(path_to_zip: str, json_output_path: str) -> str:
                from pathlib import Path
                import shutil
                import json
                source_to_compress = Path(path_to_zip).expanduser().absolute()
                archive_base_path = source_to_compress.parent / (source_to_compress.name + "_archive")
                if source_to_compress.is_dir():
                    shutil.make_archive(str(archive_base_path), "zip", source_to_compress)
                else:
                    shutil.make_archive(str(archive_base_path), "zip", source_to_compress.parent, source_to_compress.name)
                zip_file_path = str(archive_base_path) + ".zip"
                json_result_path = Path(json_output_path)
                json_result_path.parent.mkdir(parents=True, exist_ok=True)
                json_result_path.write_text(json.dumps(zip_file_path, indent=2), encoding="utf-8")
                print(json_result_path.as_posix())
                return zip_file_path

            remote_json_output = Path.home().joinpath(f"{DEFAULT_PICKLE_SUBDIR}/return_{randstr()}.json").as_posix()
            command = lambda_to_python_script(
                lambda: zip_source(path_to_zip=expanded_source, json_output_path=remote_json_output),
                in_global=True, import_module=False,
            )
            response = self.run_py_remotely(
                python_code=command,
                uv_with=[STACKOPS_REQUIREMENT],
                uv_project_dir=None,
                description=f"Zipping source file {source}",
                verbose_output=False,
                strict_stderr=False,
                strict_return_code=False,
            )
            remote_json_path = response.op.strip()
            if not remote_json_path:
                raise RuntimeError(f"Could not zip {source} - no response from remote")
            local_json = Path.home().joinpath(f"{DEFAULT_PICKLE_SUBDIR}/local_{randstr()}.json")
            self.simple_sftp_get(remote_path=remote_json_path, local_path=local_json)
            import json
            try:
                zipped_path = json.loads(local_json.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, FileNotFoundError) as err:
                raise RuntimeError(f"Could not zip {source} - invalid JSON response: {err}") from err
            finally:
                if local_json.exists():
                    local_json.unlink()
            assert isinstance(zipped_path, str), f"Could not zip {source}"
            source_obj = Path(zipped_path)
            expanded_source = zipped_path
        if target is None:
            def collapse_to_home(absolute_path: str, json_output_path: str) -> str:
                from pathlib import Path
                import json
                source_absolute_path = Path(absolute_path).expanduser().absolute()
                try:
                    relative_to_home = source_absolute_path.relative_to(Path.home())
                    collapsed_path_posix = (Path("~") / relative_to_home).as_posix()
                    json_result_path = Path(json_output_path)
                    json_result_path.parent.mkdir(parents=True, exist_ok=True)
                    json_result_path.write_text(json.dumps(collapsed_path_posix, indent=2), encoding="utf-8")
                    print(json_result_path.as_posix())
                    return collapsed_path_posix
                except ValueError:
                    raise RuntimeError(f"Source path must be relative to home directory: {source_absolute_path}")

            remote_json_output = Path.home().joinpath(f"{DEFAULT_PICKLE_SUBDIR}/return_{randstr()}.json").as_posix()
            command = lambda_to_python_script(
                lambda: collapse_to_home(absolute_path=expanded_source, json_output_path=remote_json_output),
                in_global=True, import_module=False,
            )
            response = self.run_py_remotely(
                python_code=command,
                uv_with=[STACKOPS_REQUIREMENT],
                uv_project_dir=None,
                description="Finding default target via relative source path",
                verbose_output=False,
                strict_stderr=False,
                strict_return_code=False,
            )
            remote_json_path = response.op.strip()
            if not remote_json_path:
                raise RuntimeError("Could not resolve target path - no response from remote")
            local_json = Path.home().joinpath(f"{DEFAULT_PICKLE_SUBDIR}/local_{randstr()}.json")
            self.simple_sftp_get(remote_path=remote_json_path, local_path=local_json)
            import json
            try:
                target_str = json.loads(local_json.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, FileNotFoundError) as err:
                raise RuntimeError(f"Could not resolve target path - invalid JSON response: {err}") from err
            finally:
                if local_json.exists():
                    local_json.unlink()
            assert isinstance(target_str, str), "Could not resolve target path"
            target = Path(target_str)
            assert str(target).startswith("~"), f"If target is not specified, source must be relative to home.\n{target=}"
        target_obj = Path(target).expanduser().absolute()
        target_obj.parent.mkdir(parents=True, exist_ok=True)
        if compress_with_zip and target_obj.suffix != ".zip":
            target_obj = target_obj.with_suffix(target_obj.suffix + ".zip")
        print(f"""[DOWNLOAD] Receiving: {expanded_source}  ==>  Local Path: {target_obj}""")
        try:
            with self.tqdm_wrap(ascii=True, unit="b", unit_scale=True) as pbar:
                sftp.get(remotepath=expanded_source, localpath=str(target_obj), callback=pbar.view_bar)
        except Exception:
            if target_obj.exists():
                target_obj.unlink()
            raise
        if compress_with_zip:
            import zipfile
            extract_to = target_obj.parent / target_obj.stem
            with zipfile.ZipFile(target_obj, "r") as zip_ref:
                zip_ref.extractall(extract_to)
            target_obj.unlink()
            target_obj = extract_to

            def delete_temp_zip(path_to_delete: str) -> None:
                from pathlib import Path
                import shutil
                file_or_dir_path = Path(path_to_delete)
                if file_or_dir_path.exists():
                    if file_or_dir_path.is_dir():
                        shutil.rmtree(file_or_dir_path)
                    else:
                        file_or_dir_path.unlink()

            command = lambda_to_python_script(
                lambda: delete_temp_zip(path_to_delete=expanded_source),
                in_global=True, import_module=False,
            )
            self.run_py_remotely(
                python_code=command,
                uv_with=[STACKOPS_REQUIREMENT],
                uv_project_dir=None,
                description="Cleaning temp zip files @ remote.",
                verbose_output=False,
                strict_stderr=True,
                strict_return_code=True,
            )
        print("\n")
        return None


if __name__ == "__main__":
    ssh = SSH(host="p51s", username=None, hostname=None, ssh_key_path=None, password=None, port=22, enable_compression=False)
