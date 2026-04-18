from __future__ import annotations

import subprocess

import pytest

from stackops.utils import options as options_module


def test_choose_from_options_returns_default_on_empty_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("builtins.input", lambda _prompt: "")

    choice = options_module.choose_from_options(
        options=[1, 2, 3],
        msg="Pick one",
        multi=False,
        default=2,
        tv=False,
    )

    assert choice == 2


def test_choose_from_options_rejects_unknown_choice_when_custom_input_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("builtins.input", lambda _prompt: "missing")

    choice = options_module.choose_from_options(
        options=["alpha", "beta"],
        msg="Pick one",
        multi=False,
        custom_input=False,
        tv=False,
    )

    assert choice is None


def test_choose_cloud_interactively_parses_rclone_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_run(
        command: str,
        *,
        shell: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        assert command == "rclone listremotes"
        assert shell is True
        assert capture_output is True
        assert text is True
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="work:\nplay:\n",
            stderr="",
        )

    def fake_choose_from_options(
        *,
        msg: str,
        options: list[str],
        multi: bool,
        default: str,
        tv: bool,
    ) -> str | None:
        captured["msg"] = msg
        captured["options"] = options
        captured["multi"] = multi
        captured["default"] = default
        captured["tv"] = tv
        return "play"

    monkeypatch.setattr(options_module.subprocess, "run", fake_run)
    monkeypatch.setattr(options_module, "choose_from_options", fake_choose_from_options)

    cloud = options_module.choose_cloud_interactively()

    assert cloud == "play"
    assert captured["options"] == ["work", "play"]
    assert captured["default"] == "work"
    assert captured["multi"] is False
    assert captured["tv"] is True


def test_choose_ssh_host_delegates_multi_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    multi_calls: list[bool] = []

    def fake_choose_from_options(
        *,
        msg: str,
        options: list[str],
        multi: bool,
        tv: bool,
    ) -> str | list[str] | None:
        assert msg == ""
        assert options == ["box-a", "box-b"]
        assert tv is True
        multi_calls.append(multi)
        if multi:
            return ["box-a"]
        return "box-a"

    monkeypatch.setattr(options_module, "get_ssh_hosts", lambda: ["box-a", "box-b"])
    monkeypatch.setattr(options_module, "choose_from_options", fake_choose_from_options)

    assert options_module.choose_ssh_host(multi=False) == "box-a"
    assert options_module.choose_ssh_host(multi=True) == ["box-a"]
    assert multi_calls == [False, True]
