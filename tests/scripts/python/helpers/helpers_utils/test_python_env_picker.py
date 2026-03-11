from machineconfig.scripts.python.helpers.helpers_utils import python as helpers_python


def test_tui_env_uses_textual_when_requested(monkeypatch) -> None:
    calls: list[str] = []

    def fake_run_textual(which: str) -> None:
        calls.append(which)

    monkeypatch.setattr(helpers_python, "_run_textual_env", fake_run_textual)

    helpers_python.tui_env(which="ENV", tui=True)

    assert calls == ["ENV"]


def test_tui_env_uses_tv_by_default_and_echoes_selection(monkeypatch, capsys) -> None:
    calls: list[str] = []

    def fake_choose_with_tv(which: str) -> tuple[bool, str | None]:
        return True, "/usr/bin"

    def fake_run_textual(which: str) -> None:
        calls.append(which)

    monkeypatch.setattr(helpers_python, "_choose_with_tv", fake_choose_with_tv)
    monkeypatch.setattr(helpers_python, "_run_textual_env", fake_run_textual)

    helpers_python.tui_env(which="PATH", tui=False)

    captured = capsys.readouterr()
    assert captured.out == "/usr/bin\n"
    assert calls == []


def test_tui_env_cancelled_tv_picker_does_not_fallback(monkeypatch, capsys) -> None:
    calls: list[str] = []

    def fake_choose_with_tv(which: str) -> tuple[bool, str | None]:
        return True, None

    def fake_run_textual(which: str) -> None:
        calls.append(which)

    monkeypatch.setattr(helpers_python, "_choose_with_tv", fake_choose_with_tv)
    monkeypatch.setattr(helpers_python, "_run_textual_env", fake_run_textual)

    helpers_python.tui_env(which="ENV", tui=False)

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert calls == []


def test_tui_env_falls_back_to_textual_when_tv_is_unavailable(monkeypatch, capsys) -> None:
    calls: list[str] = []

    def fake_choose_with_tv(which: str) -> tuple[bool, str | None]:
        return False, None

    def fake_run_textual(which: str) -> None:
        calls.append(which)

    monkeypatch.setattr(helpers_python, "_choose_with_tv", fake_choose_with_tv)
    monkeypatch.setattr(helpers_python, "_run_textual_env", fake_run_textual)

    helpers_python.tui_env(which="PATH", tui=False)

    captured = capsys.readouterr()
    assert "tv picker unavailable" in captured.err
    assert calls == ["PATH"]
