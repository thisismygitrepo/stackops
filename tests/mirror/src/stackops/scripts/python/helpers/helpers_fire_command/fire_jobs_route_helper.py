import builtins
import sys
import types
from pathlib import Path

import pytest

import stackops.scripts.python.helpers.helpers_fire_command.fire_jobs_route_helper as subject

_PARSE_MODULE = "stackops.scripts.python.helpers.helpers_fire_command.file_wrangler"
_ADDRESS_MODULE = "stackops.scripts.python.helpers.helpers_network.address"
_INSTALLER_MODULE = "stackops.utils.installer_utils.installer_cli"
_CODE_MODULE = "stackops.utils.code"


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


def _install_rich_stubs(monkeypatch: pytest.MonkeyPatch, printed: list[object]) -> None:
    rich_module = types.ModuleType("rich")
    panel_module = types.ModuleType("rich.panel")

    def fake_print(*objects: object) -> None:
        printed.extend(objects)

    setattr(rich_module, "print", fake_print)
    setattr(panel_module, "Panel", FakePanel)
    monkeypatch.setitem(sys.modules, "rich", rich_module)
    monkeypatch.setitem(sys.modules, "rich.panel", panel_module)


def test_choose_function_or_lines_collects_missing_kwargs_for_python_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    choice_file = tmp_path / "job.py"
    choice_file.write_text("pass\n", encoding="utf-8")

    def fake_parse_pyfile(*, file_path: str) -> tuple[list[str], list[list[types.SimpleNamespace]]]:
        assert file_path == str(choice_file)
        return (
            ["deploy -- docs"],
            [[types.SimpleNamespace(name="user", type="str", default="alex")]],
        )

    def fake_choose_from_options(*, msg: str, options: list[str], tv: bool, multi: bool) -> str:
        assert msg == "Choose a function to run"
        assert options == ["deploy -- docs"]
        assert tv is True
        assert multi is False
        return options[0]

    fake_module = types.ModuleType(_PARSE_MODULE)
    setattr(fake_module, "parse_pyfile", fake_parse_pyfile)
    monkeypatch.setitem(sys.modules, _PARSE_MODULE, fake_module)
    monkeypatch.setattr(subject, "choose_from_options", fake_choose_from_options)
    monkeypatch.setattr(builtins, "input", lambda _prompt: "")

    choice_function, resolved_file, kwargs_dict = subject.choose_function_or_lines(choice_file, {})

    assert choice_function == "deploy"
    assert resolved_file == choice_file
    assert kwargs_dict == {"user": "alex"}


def test_choose_function_or_lines_returns_none_for_run_as_main(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    choice_file = tmp_path / "job.py"
    choice_file.write_text("pass\n", encoding="utf-8")

    def fake_parse_pyfile(*, file_path: str) -> tuple[list[str], list[list[types.SimpleNamespace]]]:
        assert file_path == str(choice_file)
        return (["RUN AS MAIN -- script"], [[]])

    def fake_choose_from_options(*, msg: str, options: list[str], tv: bool, multi: bool) -> str:
        assert msg == "Choose a function to run"
        assert options == ["RUN AS MAIN -- script"]
        assert tv is True
        assert multi is False
        return options[0]

    fake_module = types.ModuleType(_PARSE_MODULE)
    setattr(fake_module, "parse_pyfile", fake_parse_pyfile)
    monkeypatch.setitem(sys.modules, _PARSE_MODULE, fake_module)
    monkeypatch.setattr(subject, "choose_from_options", fake_choose_from_options)

    choice_function, resolved_file, kwargs_dict = subject.choose_function_or_lines(choice_file, {"preset": "yes"})

    assert choice_function is None
    assert resolved_file == choice_file
    assert kwargs_dict == {"preset": "yes"}


def test_choose_function_or_lines_writes_selected_shell_lines(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    choice_file = tmp_path / "job.sh"
    choice_file.write_text("# ignore\n\necho hidden\nprintf 'hi'\nls -la\n", encoding="utf-8")
    seen_options: list[str] = []

    def fake_choose_from_options(*, msg: str, options: list[str], tv: bool, multi: bool) -> list[str]:
        assert msg == "Choose a line to run"
        assert tv is True
        assert multi is True
        seen_options.extend(options)
        return ["ls -la"]

    monkeypatch.setattr(subject, "choose_from_options", fake_choose_from_options)
    monkeypatch.setattr(subject, "randstr", lambda _size: "fixed-name")
    monkeypatch.setattr(subject.Path, "home", classmethod(lambda _cls: tmp_path))

    choice_function, resolved_file, kwargs_dict = subject.choose_function_or_lines(choice_file, {})

    expected_file = tmp_path / "tmp_results/tmp_scripts/shell/fixed-name.sh"
    assert choice_function is None
    assert resolved_file == expected_file
    assert kwargs_dict == {}
    assert seen_options == ["printf 'hi'", "ls -la"]
    assert expected_file.read_text(encoding="utf-8") == "ls -la"


def test_get_command_streamlit_reads_pages_parent_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    page_file = tmp_path / "demo/pages/dashboard.py"
    page_file.parent.mkdir(parents=True, exist_ok=True)
    page_file.write_text("pass\n", encoding="utf-8")
    config_dir = tmp_path / "demo/.streamlit"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_dir.joinpath("config.toml").write_text("[server]\nport = 9999\n", encoding="utf-8")

    printed: list[object] = []
    installer_calls: list[tuple[str, str | None, bool]] = []
    code_calls: list[tuple[str, str, str]] = []

    def fake_select_lan_ipv4(*, prefer_vpn: bool) -> str:
        assert prefer_vpn is False
        return "192.168.1.25"

    def fake_install_if_missing(*, which: str, binary_name: str | None, verbose: bool) -> None:
        installer_calls.append((which, binary_name, verbose))

    def fake_print_code(*, code: str, lexer: str, desc: str) -> None:
        code_calls.append((code, lexer, desc))

    address_module = types.ModuleType(_ADDRESS_MODULE)
    installer_module = types.ModuleType(_INSTALLER_MODULE)
    code_module = types.ModuleType(_CODE_MODULE)
    setattr(address_module, "select_lan_ipv4", fake_select_lan_ipv4)
    setattr(installer_module, "install_if_missing", fake_install_if_missing)
    setattr(code_module, "print_code", fake_print_code)
    monkeypatch.setitem(sys.modules, _ADDRESS_MODULE, address_module)
    monkeypatch.setitem(sys.modules, _INSTALLER_MODULE, installer_module)
    monkeypatch.setitem(sys.modules, _CODE_MODULE, code_module)
    _install_rich_stubs(monkeypatch, printed)
    monkeypatch.setattr(subject.platform, "node", lambda: "devbox")

    result = subject.get_command_streamlit(page_file, environment="", repo_root=None)

    assert result == "streamlit run --server.address 0.0.0.0 --server.headless true --server.port 9999"
    assert installer_calls == [("qrterminal", None, True)]
    assert len(code_calls) == 1
    assert "http://192.168.1.25:9999" in code_calls[0][0]
    assert "http://devbox:9999" in code_calls[0][0]
    assert isinstance(printed[0], FakePanel)
    assert "http://localhost:9999" in str(printed[0].renderable)


def test_get_command_streamlit_raises_when_no_lan_ip(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    address_module = types.ModuleType(_ADDRESS_MODULE)
    setattr(address_module, "select_lan_ipv4", lambda *, prefer_vpn: None)
    monkeypatch.setitem(sys.modules, _ADDRESS_MODULE, address_module)

    with pytest.raises(RuntimeError, match="Could not determine local LAN IPv4 address"):
        subject.get_command_streamlit(tmp_path / "app.py", environment="", repo_root=None)
