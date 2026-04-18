import importlib.util
import sys
import types
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

_SOURCE_FILE = Path(__file__).resolve().parents[9] / "src/stackops/scripts/python/helpers/helpers_network/ssh/ssh_add_ssh_key.py"
_WINDOWS_HELPER_MODULE = "stackops.scripts.python.helpers.helpers_network.ssh.ssh_add_key_windows"
_CLOUD_INIT_MODULE = "stackops.scripts.python.helpers.helpers_network.ssh.ssh_cloud_init"
_DEPLOY_MODULE = "stackops.scripts.python.helpers.helpers_network.ssh.ssh_deploy_key_remote"
_CODE_MODULE = "stackops.utils.code"
_ADDRESS_MODULE = "stackops.scripts.python.helpers.helpers_network.address"
_TARGET_MODULE_NAME = "mirror_target_ssh_add_ssh_key"


class FakeConsole:
    def __init__(self) -> None:
        self.records: list[object] = []

    def print(self, *objects: object, **_kwargs: object) -> None:
        self.records.extend(objects)


class FakePanel:
    def __init__(
        self,
        renderable: object,
        title: str = "",
        border_style: str = "",
        box: object | None = None,
    ) -> None:
        self.renderable = renderable
        self.title = title
        self.border_style = border_style
        self.box = box



def _load_subject(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    rich_module = types.ModuleType("rich")
    rich_console_module = types.ModuleType("rich.console")
    rich_panel_module = types.ModuleType("rich.panel")
    setattr(rich_module, "box", types.SimpleNamespace(DOUBLE_EDGE="double-edge"))
    setattr(rich_console_module, "Console", FakeConsole)
    setattr(rich_panel_module, "Panel", FakePanel)
    monkeypatch.setitem(sys.modules, "rich", rich_module)
    monkeypatch.setitem(sys.modules, "rich.console", rich_console_module)
    monkeypatch.setitem(sys.modules, "rich.panel", rich_panel_module)

    windows_helper_module = types.ModuleType(_WINDOWS_HELPER_MODULE)
    cloud_init_module = types.ModuleType(_CLOUD_INIT_MODULE)
    deploy_module = types.ModuleType(_DEPLOY_MODULE)

    def fake_add_ssh_key_windows(_path_to_key: Path) -> None:
        return None

    def fake_check_cloud_init_overrides() -> tuple[list[Path], dict[str, tuple[Path, str]]]:
        return ([], {})

    def fake_generate_cloud_init_fix_script(_auth_overrides: dict[str, tuple[Path, str]]) -> str:
        return ""

    def fake_deploy_key_to_remote(*, remote_target: str, pubkey_path: Path, password: str | None) -> bool:
        return True

    def fake_deploy_multiple_keys_to_remote(*, remote_target: str, pubkey_paths: list[Path], password: str | None) -> bool:
        return True

    setattr(windows_helper_module, "add_ssh_key_windows", fake_add_ssh_key_windows)
    setattr(cloud_init_module, "check_cloud_init_overrides", fake_check_cloud_init_overrides)
    setattr(cloud_init_module, "generate_cloud_init_fix_script", fake_generate_cloud_init_fix_script)
    setattr(deploy_module, "deploy_key_to_remote", fake_deploy_key_to_remote)
    setattr(deploy_module, "deploy_multiple_keys_to_remote", fake_deploy_multiple_keys_to_remote)
    monkeypatch.setitem(sys.modules, _WINDOWS_HELPER_MODULE, windows_helper_module)
    monkeypatch.setitem(sys.modules, _CLOUD_INIT_MODULE, cloud_init_module)
    monkeypatch.setitem(sys.modules, _DEPLOY_MODULE, deploy_module)
    sys.modules.pop(_TARGET_MODULE_NAME, None)
    spec = importlib.util.spec_from_file_location(_TARGET_MODULE_NAME, _SOURCE_FILE)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module



def test_get_add_ssh_key_script_skips_duplicate_key_on_linux(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_subject(monkeypatch)
    get_add_ssh_key_script = cast(Callable[[Path], tuple[str, str]], getattr(module, "get_add_ssh_key_script"))
    path_cls = cast(type[Path], getattr(module, "Path"))
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir(parents=True, exist_ok=True)
    key_path = tmp_path / "id.pub"
    key_text = "ssh-ed25519 AAAATEST"
    key_path.write_text(key_text, encoding="utf-8")
    ssh_dir.joinpath("authorized_keys").write_text(f"{key_text}\n", encoding="utf-8")
    monkeypatch.setattr(module, "system", lambda: "Linux")
    monkeypatch.setattr(path_cls, "home", classmethod(lambda _cls: tmp_path))

    program, status = get_add_ssh_key_script(key_path)

    assert "already authorized" in status
    assert f"cat {key_path}" not in program
    assert "sudo chmod 700 ~/.ssh" in program



def test_get_add_ssh_key_script_on_windows_uses_python_helper(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_subject(monkeypatch)
    get_add_ssh_key_script = cast(Callable[[Path], tuple[str, str]], getattr(module, "get_add_ssh_key_script"))
    key_path = tmp_path / "id.pub"
    key_path.write_text("ssh-rsa KEY", encoding="utf-8")
    called_paths: list[Path] = []
    windows_auth_file = tmp_path / "administrators_authorized_keys"

    def fake_path(value: str) -> Path:
        if value == "C:/ProgramData/ssh/administrators_authorized_keys":
            return windows_auth_file
        return Path(value)

    monkeypatch.setattr(module, "system", lambda: "Windows")
    monkeypatch.setattr(module, "Path", fake_path)
    monkeypatch.setattr(module, "add_ssh_key_windows", lambda path_to_key: called_paths.append(path_to_key))

    program, status = get_add_ssh_key_script(key_path)

    assert program == ""
    assert called_paths == [key_path]
    assert "Windows" in status



def test_main_runs_generated_script_and_reports_lan_ip(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_subject(monkeypatch)
    main = cast(Callable[[str | None, bool, bool, str | None, str | None], None], getattr(module, "main"))
    key_path = tmp_path / "id.pub"
    key_path.write_text("ssh-ed25519 KEY", encoding="utf-8")
    run_calls: list[tuple[str, bool, bool]] = []
    address_calls: list[bool] = []
    code_module = types.ModuleType(_CODE_MODULE)
    address_module = types.ModuleType(_ADDRESS_MODULE)

    def fake_run_shell_script(*, script: str, display_script: bool, clean_env: bool) -> None:
        run_calls.append((script, display_script, clean_env))

    def fake_select_lan_ipv4(*, prefer_vpn: bool) -> str:
        address_calls.append(prefer_vpn)
        return "10.0.0.5"

    setattr(code_module, "run_shell_script", fake_run_shell_script)
    setattr(address_module, "select_lan_ipv4", fake_select_lan_ipv4)
    monkeypatch.setitem(sys.modules, _CODE_MODULE, code_module)
    existing_address_module = sys.modules.get(_ADDRESS_MODULE)
    if existing_address_module is not None:
        monkeypatch.setattr(existing_address_module, "select_lan_ipv4", fake_select_lan_ipv4)
    else:
        monkeypatch.setitem(sys.modules, _ADDRESS_MODULE, address_module)
    monkeypatch.setattr(module, "get_add_ssh_key_script", lambda _key: ("echo ok", "Status block"))

    main(
        pub_path=str(key_path),
        pub_choose=False,
        pub_val=False,
        from_github=None,
        remote=None,
    )

    assert run_calls == [("echo ok", True, False)]
    assert address_calls == [False]
