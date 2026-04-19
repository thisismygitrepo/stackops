

import sys
from pathlib import Path
from types import ModuleType
from typing import Generic, TypeVar

import pytest
from questionary import Choice

from stackops.scripts.python.helpers.helpers_devops import interactive as module_under_test


PromptValueT = TypeVar("PromptValueT")


class FakePrompt(Generic[PromptValueT]):
    def __init__(self, value: PromptValueT | None) -> None:
        self._value = value

    def ask(self) -> PromptValueT | None:
        return self._value


def install_stub_module(monkeypatch: pytest.MonkeyPatch, module_name: str, attributes: dict[str, object]) -> ModuleType:
    stub = ModuleType(module_name)
    for attribute_name, attribute_value in attributes.items():
        setattr(stub, attribute_name, attribute_value)
    monkeypatch.setitem(sys.modules, module_name, stub)
    return stub


def test_get_installation_choices_returns_checkbox_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_prompt: list[str] = []
    captured_choices: list[Choice] = []
    captured_show_description: list[bool] = []

    def fake_checkbox(message: str, *, choices: list[Choice], show_description: bool) -> FakePrompt[list[module_under_test.InstallOption]]:
        captured_prompt.append(message)
        captured_choices.extend(choices)
        captured_show_description.append(show_description)
        return FakePrompt(["termabc", "retrieve_data"])

    monkeypatch.setattr(module_under_test.questionary, "checkbox", fake_checkbox)

    selected = module_under_test.get_installation_choices()

    assert selected == ["termabc", "retrieve_data"]
    assert captured_prompt == ["Select the installation options you want to execute:"]
    assert captured_show_description == [True]
    assert [choice.value for choice in captured_choices] == [
        "install_stackops",
        "sysabc",
        "termabc",
        "install_shell_profile",
        "link_public_configs",
        "link_private_configs",
        "retrieve_repositories",
        "retrieve_data",
    ]


def test_execute_installations_runs_cli_group_installer_and_reloads_linux_shell(monkeypatch: pytest.MonkeyPatch) -> None:
    installer_calls: list[tuple[bool, str, bool]] = []
    shell_calls: list[tuple[str, bool, bool]] = []

    def fake_main_installer_cli(*, group: bool, which: str, interactive: bool) -> None:
        installer_calls.append((group, which, interactive))

    def fake_run_shell_script(script: str, *, display_script: bool, clean_env: bool) -> None:
        shell_calls.append((script, display_script, clean_env))

    install_stub_module(monkeypatch, "stackops.utils.installer_utils.installer_cli", {"main_installer_cli": fake_main_installer_cli})
    monkeypatch.setattr(module_under_test.platform, "system", lambda: "Linux")
    monkeypatch.setattr(module_under_test, "run_shell_script", fake_run_shell_script)
    monkeypatch.setattr(module_under_test.console, "print", lambda *_args, **_kwargs: None)

    module_under_test.execute_installations(selected_options=["sysabc"])

    assert installer_calls == [(True, "sysabc", False)]
    assert shell_calls == [(". $HOME/.bashrc", False, False)]


def test_execute_installations_exits_when_dotfiles_missing_and_user_chooses_exit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    home_path = tmp_path.joinpath("home")
    home_path.mkdir()
    exit_now = "Exit now and sort out dotfiles migration first."

    monkeypatch.setattr(module_under_test.console, "print", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(module_under_test.Path, "home", staticmethod(lambda: home_path))
    monkeypatch.setattr(module_under_test.questionary, "select", lambda *_args, **_kwargs: FakePrompt(exit_now))

    with pytest.raises(SystemExit) as exc_info:
        module_under_test.execute_installations(selected_options=["retrieve_data"])

    assert exc_info.value.code == 0


def test_main_executes_selected_steps_then_reloads_shell_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    execute_calls: list[list[module_under_test.InstallOption]] = []
    reload_calls: list[str] = []

    install_stub_module(
        monkeypatch, "stackops.profile.create_shell_profile", {"reload_shell_profile_and_exit": lambda: reload_calls.append("reloaded")}
    )
    monkeypatch.setattr(module_under_test.console, "print", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(module_under_test, "display_header", lambda: None)
    monkeypatch.setattr(module_under_test, "get_installation_choices", lambda: ["install_stackops"])
    monkeypatch.setattr(module_under_test.questionary, "confirm", lambda *_args, **_kwargs: FakePrompt(True))
    monkeypatch.setattr(module_under_test, "execute_installations", lambda selected_options: execute_calls.append(list(selected_options)))

    module_under_test.main()

    assert execute_calls == [["install_stackops"]]
    assert reload_calls == ["reloaded"]
