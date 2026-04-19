

import pytest

import stackops.utils.options_utils.options_tv_linux as options_tv_linux
import stackops.utils.options_utils.options_tv_windows as options_tv_windows
import stackops.utils.options_utils.tv_options as tv_options


def test_choose_from_dict_with_preview_returns_empty_values_for_empty_mapping() -> None:
    assert tv_options.choose_from_dict_with_preview({}, extension="txt", multi=False, preview_size_percent=50) is None
    assert tv_options.choose_from_dict_with_preview({}, extension="txt", multi=True, preview_size_percent=50) == []


def test_choose_from_dict_with_preview_dispatches_to_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_system() -> str:
        return "Windows"

    def fake_select_from_options(
        options_to_preview_mapping: dict[str, object],
        extension: str | None,
        multi: bool,
        preview_size_percent: float,
    ) -> str | list[str] | None:
        captured["mapping"] = options_to_preview_mapping
        captured["extension"] = extension
        captured["multi"] = multi
        captured["preview_size_percent"] = preview_size_percent
        return "picked"

    monkeypatch.setattr(tv_options.platform, "system", fake_system)
    monkeypatch.setattr(options_tv_windows, "select_from_options", fake_select_from_options)

    result = tv_options.choose_from_dict_with_preview(
        {"alpha": "preview"},
        extension="md",
        multi=False,
        preview_size_percent=25,
    )

    assert result == "picked"
    assert captured == {
        "mapping": {"alpha": "preview"},
        "extension": "md",
        "multi": False,
        "preview_size_percent": 25,
    }


def test_choose_from_dict_with_preview_dispatches_to_linux(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_system() -> str:
        return "Linux"

    def fake_select_from_options(
        *,
        options_to_preview_mapping: dict[str, object],
        extension: str | None,
        multi: bool,
        preview_size_percent: float,
    ) -> list[str]:
        captured["mapping"] = options_to_preview_mapping
        captured["extension"] = extension
        captured["multi"] = multi
        captured["preview_size_percent"] = preview_size_percent
        return ["one", "two"]

    monkeypatch.setattr(tv_options.platform, "system", fake_system)
    monkeypatch.setattr(options_tv_linux, "select_from_options", fake_select_from_options)

    result = tv_options.choose_from_dict_with_preview(
        {"alpha": "preview"},
        extension="py",
        multi=True,
        preview_size_percent=70,
    )

    assert result == ["one", "two"]
    assert captured == {
        "mapping": {"alpha": "preview"},
        "extension": "py",
        "multi": True,
        "preview_size_percent": 70,
    }
