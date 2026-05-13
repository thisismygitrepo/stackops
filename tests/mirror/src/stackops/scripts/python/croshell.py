import pytest

import stackops.scripts.python.croshell as croshell_app


def test_croshell_passes_terminal1_alias_to_impl(monkeypatch: pytest.MonkeyPatch) -> None:
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
        backend="t",
        profile=None,
        stackops_project=False,
        frozen=False,
    )

    assert captured_backends == ["terminal1"]


def test_croshell_passes_terminal2_alias_to_impl(monkeypatch: pytest.MonkeyPatch) -> None:
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
        backend="T",
        profile=None,
        stackops_project=False,
        frozen=False,
    )

    assert captured_backends == ["terminal2"]
