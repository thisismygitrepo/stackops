import getpass
import sys
import types
from pathlib import Path

import pytest

import stackops.scripts.python.helpers.helpers_network.ftpx_impl as subject

_PATH_EXTENDED_MODULE = "stackops.utils.path_extended"
_HELPERS_CLOUD_MODULE = "stackops.scripts.python.helpers.helpers_cloud.helpers2"
_WSL_MODULE = "stackops.utils.ssh_utils.wsl"
_SSH_MODULE = "stackops.utils.ssh"
_PARAMIKO_MODULE = "paramiko.ssh_exception"
_ACCESSORIES_MODULE = "stackops.utils.accessories"


class FakeConsole:
    created: list["FakeConsole"] = []

    def __init__(self) -> None:
        self.printed: list[object] = []
        type(self).created.append(self)

    def print(self, *objects: object, **_kwargs: object) -> None:
        self.printed.extend(objects)


class FakePanel:
    def __init__(
        self,
        renderable: object,
        title: str = "",
        border_style: str = "",
        padding: tuple[int, int] | None = None,
    ) -> None:
        self.renderable = renderable
        self.title = title
        self.border_style = border_style
        self.padding = padding

    @classmethod
    def fit(cls, renderable: object, title: str = "", border_style: str = "") -> "FakePanel":
        return cls(renderable, title=title, border_style=border_style)


class FakePathExtended:
    def __init__(self, value: str) -> None:
        path = Path(value).expanduser()
        self.path = path if path.is_absolute() else Path("/abs") / path

    def expanduser(self) -> "FakePathExtended":
        self.path = self.path.expanduser()
        return self

    def absolute(self) -> "FakePathExtended":
        if not self.path.is_absolute():
            self.path = Path("/abs") / self.path
        return self

    def collapseuser(self) -> "FakePathExtended":
        return self

    def as_posix(self) -> str:
        return self.path.as_posix()

    def __fspath__(self) -> str:
        return self.path.as_posix()

    @property
    def parent(self) -> Path:
        return self.path.parent

    def __repr__(self) -> str:
        return repr(self.path)

    def __str__(self) -> str:
        return self.path.as_posix()



def _install_rich_stubs(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeConsole.created.clear()
    rich_console_module = types.ModuleType("rich.console")
    rich_panel_module = types.ModuleType("rich.panel")
    setattr(rich_console_module, "Console", FakeConsole)
    setattr(rich_panel_module, "Panel", FakePanel)
    monkeypatch.setitem(sys.modules, "rich.console", rich_console_module)
    monkeypatch.setitem(sys.modules, "rich.panel", rich_panel_module)



def _install_path_extended_stubs(monkeypatch: pytest.MonkeyPatch) -> None:
    path_extended_module = types.ModuleType(_PATH_EXTENDED_MODULE)
    helpers_cloud_module = types.ModuleType(_HELPERS_CLOUD_MODULE)
    setattr(path_extended_module, "PathExtended", FakePathExtended)
    setattr(helpers_cloud_module, "ES", "^")
    monkeypatch.setitem(sys.modules, _PATH_EXTENDED_MODULE, path_extended_module)
    monkeypatch.setitem(sys.modules, _HELPERS_CLOUD_MODULE, helpers_cloud_module)



def test_handle_wsl_transfer_uses_home_relative_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[tuple[Path, Path, bool]] = []
    home = tmp_path / "home"
    file_path = home / "docs/file.txt"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("x\n", encoding="utf-8")

    def fake_copy_when_inside_windows(source_obj: Path, target_obj: Path, overwrite_existing: bool) -> None:
        calls.append((source_obj, target_obj, overwrite_existing))

    wsl_module = types.ModuleType(_WSL_MODULE)
    setattr(wsl_module, "copy_when_inside_windows", fake_copy_when_inside_windows)
    monkeypatch.setitem(sys.modules, _WSL_MODULE, wsl_module)
    monkeypatch.setattr(subject.Path, "home", classmethod(lambda _cls: home))

    subject._handle_wsl_transfer(source=str(file_path), target="wsl", overwrite_existing=True)

    assert calls == [(Path("docs/file.txt"), Path("docs/file.txt"), True)]



def test_handle_win_transfer_uses_home_relative_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[tuple[Path, Path, bool, str | None]] = []
    home = tmp_path / "home"
    file_path = home / "docs/file.txt"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("x\n", encoding="utf-8")

    def fake_copy_when_inside_wsl(
        source_obj: Path,
        target_obj: Path,
        overwrite_existing: bool,
        *,
        windows_username: str | None,
    ) -> None:
        calls.append((source_obj, target_obj, overwrite_existing, windows_username))

    wsl_module = types.ModuleType(_WSL_MODULE)
    setattr(wsl_module, "copy_when_inside_wsl", fake_copy_when_inside_wsl)
    monkeypatch.setitem(sys.modules, _WSL_MODULE, wsl_module)
    monkeypatch.setattr(subject.Path, "home", classmethod(lambda _cls: home))

    subject._handle_win_transfer(source=str(file_path), target="win", overwrite_existing=False, windows_username=None)

    assert calls == [(Path("docs/file.txt"), Path("docs/file.txt"), False, None)]



def test_resolve_paths_handles_expand_symbol_from_remote_source(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_path_extended_stubs(monkeypatch)

    result = subject._resolve_paths(source="box:^", target="/local/file.txt")

    assert result == ("/local/file.txt", "/local/file.txt", "box", True)



def test_resolve_paths_handles_expand_symbol_from_local_source(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_path_extended_stubs(monkeypatch)

    result = subject._resolve_paths(source="^", target="box:remote/file.txt")

    assert result == (None, "remote/file.txt", "box", False)



def test_resolve_paths_rejects_expand_symbol_on_both_sides(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_path_extended_stubs(monkeypatch)

    with pytest.raises(ValueError, match="Cannot use expand symbol"):
        subject._resolve_paths(source="box:^", target="^")



def test_create_ssh_connection_retries_with_password(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_rich_stubs(monkeypatch)
    calls: list[str | None] = []

    class AuthenticationException(Exception):
        pass

    def fake_ssh(
        *,
        host: str,
        username: str | None,
        hostname: str | None,
        ssh_key_path: str | None,
        password: str | None,
        port: int,
        enable_compression: bool,
    ) -> str:
        assert host == "box"
        assert username is None
        assert hostname is None
        assert ssh_key_path is None
        assert port == 22
        assert enable_compression is True
        calls.append(password)
        if len(calls) == 1:
            raise AuthenticationException("bad auth")
        return "ssh-connection"

    ssh_module = types.ModuleType(_SSH_MODULE)
    paramiko_module = types.ModuleType(_PARAMIKO_MODULE)
    setattr(ssh_module, "SSH", fake_ssh)
    setattr(paramiko_module, "AuthenticationException", AuthenticationException)
    monkeypatch.setitem(sys.modules, _SSH_MODULE, ssh_module)
    monkeypatch.setitem(sys.modules, _PARAMIKO_MODULE, paramiko_module)
    monkeypatch.setattr(getpass, "getpass", lambda: "secret")
    console = FakeConsole()

    result = subject._create_ssh_connection(machine="box", console=console)

    assert result == "ssh-connection"
    assert calls == [None, "secret"]



def test_handle_cloud_transfer_runs_remote_then_local_copy(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_path_extended_stubs(monkeypatch)
    _install_rich_stubs(monkeypatch)
    remote_calls: list[str] = []
    local_calls: list[str] = []

    class FakeSSH:
        def run_shell_cmd_on_remote(
            self,
            *,
            command: str,
            verbose_output: bool,
            description: str,
            strict_stderr: bool,
            strict_return_code: bool,
        ) -> None:
            assert verbose_output is True
            assert description == "Uploading from remote to the cloud."
            assert strict_stderr is False
            assert strict_return_code is False
            remote_calls.append(command)

        def run_shell_cmd_on_local(self, *, command: str) -> None:
            local_calls.append(command)

    result = subject._handle_cloud_transfer(
        ssh=FakeSSH(),
        resolved_source="/remote/file.txt",
        resolved_target="/local/file.txt",
        console=FakeConsole(),
    )

    assert remote_calls == ["cloud copy /remote/file.txt :^"]
    assert local_calls == ["cloud copy :^ /local/file.txt"]
    assert str(result) == "/local/file.txt"



def test_handle_direct_transfer_downloads_remote_file(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_path_extended_stubs(monkeypatch)
    _install_rich_stubs(monkeypatch)
    copy_calls: list[tuple[str, str | None, bool, bool]] = []

    class FakeSSH:
        def copy_to_here(self, *, source: str, target: str | None, compress_with_zip: bool, recursive: bool) -> None:
            copy_calls.append((source, target, compress_with_zip, recursive))

    result = subject._handle_direct_transfer(
        ssh=FakeSSH(),
        resolved_source="/remote/file.txt",
        resolved_target="/local/file.txt",
        source_is_remote=True,
        zipFirst=True,
        recursive=False,
        overwrite_existing=False,
        console=FakeConsole(),
    )

    assert copy_calls == [("/remote/file.txt", "/local/file.txt", True, False)]
    assert str(result) == "/local/file.txt"



def test_handle_direct_transfer_uploads_local_file(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_rich_stubs(monkeypatch)
    copy_calls: list[tuple[str, str | None, bool, bool, bool]] = []

    class FakeSSH:
        def copy_from_here(
            self,
            *,
            source_path: str,
            target_rel2home: str | None,
            compress_with_zip: bool,
            recursive: bool,
            overwrite_existing: bool,
        ) -> None:
            copy_calls.append((source_path, target_rel2home, compress_with_zip, recursive, overwrite_existing))

    result = subject._handle_direct_transfer(
        ssh=FakeSSH(),
        resolved_source="/local/file.txt",
        resolved_target="remote/file.txt",
        source_is_remote=False,
        zipFirst=False,
        recursive=True,
        overwrite_existing=True,
        console=FakeConsole(),
    )

    assert copy_calls == [("/local/file.txt", "remote/file.txt", False, True, True)]
    assert result is None



def test_ftpx_dispatches_to_wsl_handler(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, bool]] = []

    def fake_handle_wsl_transfer(*, source: str, target: str, overwrite_existing: bool) -> None:
        calls.append((source, target, overwrite_existing))

    monkeypatch.setattr(subject, "_handle_wsl_transfer", fake_handle_wsl_transfer)

    subject.ftpx(
        source="/tmp/data.txt",
        target="wsl",
        recursive=False,
        zipFirst=False,
        cloud=False,
        overwrite_existing=True,
    )

    assert calls == [("/tmp/data.txt", "wsl", True)]



def test_ftpx_regular_flow_uses_direct_transfer(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_rich_stubs(monkeypatch)
    _install_path_extended_stubs(monkeypatch)
    accessories_module = types.ModuleType(_ACCESSORIES_MODULE)
    direct_calls: list[tuple[str | None, bool, bool, bool]] = []
    setattr(accessories_module, "pprint", lambda _payload, _desc: None)
    monkeypatch.setitem(sys.modules, _ACCESSORIES_MODULE, accessories_module)
    monkeypatch.setattr(subject, "_resolve_paths", lambda *, source, target: ("/remote/file.txt", "/local/file.txt", "box", True))
    monkeypatch.setattr(subject, "_create_ssh_connection", lambda *, machine, console: object())

    def fake_handle_direct_transfer(
        *,
        ssh: object,
        resolved_source: str | None,
        resolved_target: str | None,
        source_is_remote: bool,
        zipFirst: bool,
        recursive: bool,
        overwrite_existing: bool,
        console: FakeConsole,
    ) -> FakePathExtended:
        direct_calls.append((resolved_source, source_is_remote, zipFirst, recursive))
        assert resolved_target == "/local/file.txt"
        assert overwrite_existing is False
        return FakePathExtended("/local/file.txt")

    monkeypatch.setattr(subject, "_handle_direct_transfer", fake_handle_direct_transfer)

    subject.ftpx(
        source="box:/remote/file.txt",
        target="/local/file.txt",
        recursive=True,
        zipFirst=False,
        cloud=False,
        overwrite_existing=False,
    )

    assert direct_calls == [("/remote/file.txt", True, False, True)]
    assert FakeConsole.created
