import pytest

import stackops.scripts.python.croshell as croshell_app


def test_croshell_passes_auto1_alias_to_impl(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_backends: list[str] = []

    def fake_croshell(
        *,
        path: str | None,
        project_path: str | None,
        uv_with: str | None,
        backend: str,
        profile: str | None,
        frozen: bool,
    ) -> None:
        _ = path, project_path, uv_with, profile, frozen
        captured_backends.append(backend)

    monkeypatch.setattr("stackops.scripts.python.helpers.helpers_croshell.croshell_impl.croshell", fake_croshell)

    croshell_app.croshell(
        path="demo.txt",
        project_path=None,
        uv_with=None,
        backend="a1",
        profile=None,
        stackops_project=False,
        frozen=False,
    )

    assert captured_backends == ["auto1"]


def test_croshell_passes_auto2_alias_to_impl(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_backends: list[str] = []

    def fake_croshell(
        *,
        path: str | None,
        project_path: str | None,
        uv_with: str | None,
        backend: str,
        profile: str | None,
        frozen: bool,
    ) -> None:
        _ = path, project_path, uv_with, profile, frozen
        captured_backends.append(backend)

    monkeypatch.setattr("stackops.scripts.python.helpers.helpers_croshell.croshell_impl.croshell", fake_croshell)

    croshell_app.croshell(
        path="demo.txt",
        project_path=None,
        uv_with=None,
        backend="a2",
        profile=None,
        stackops_project=False,
        frozen=False,
    )

    assert captured_backends == ["auto2"]


def test_interactive_backend_options_show_actual_backend_names() -> None:
    options = croshell_app._interactive_backend_options(path="demo.db")

    assert "browser" in options
    assert "glow" in options
    assert "rainfrog" in options
    assert "lazysql" in options
    assert "dblab" in options
    assert "usql" in options
    assert "harlequin" in options
    assert "sqlit" in options
    assert "auto2" not in options
    assert not any(option.startswith("auto2:") for option in options)


def test_interactive_auto2_db_choice_passes_backend_to_impl(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, object]] = []

    def fake_choose_from_options(**kwargs: object) -> str:
        assert "usql" in kwargs["options"]
        return "usql"

    def fake_croshell(**kwargs: object) -> None:
        captured.append(kwargs)

    monkeypatch.setattr("stackops.utils.options.choose_from_options", fake_choose_from_options)
    monkeypatch.setattr("stackops.scripts.python.helpers.helpers_croshell.croshell_impl.croshell", fake_croshell)

    croshell_app.croshell(
        path="demo.db",
        project_path=None,
        uv_with=None,
        backend="ipython",
        interactive=True,
        profile=None,
        stackops_project=False,
        frozen=False,
    )

    assert captured == [
        {
            "path": "demo.db",
            "project_path": None,
            "uv_with": None,
            "backend": "auto2",
            "profile": None,
            "frozen": False,
            "auto2_mode": "database",
            "auto2_db_backend": "usql",
        }
    ]
