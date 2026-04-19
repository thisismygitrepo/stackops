

import pytest

from stackops.scripts.python.helpers.helpers_devops import devops_status as module


def test_resolve_sections_returns_requested_order() -> None:
    sections = module.resolve_sections(machine=False, shell=True, repos=False, ssh=True, configs=False, apps=True, backup=False)

    assert sections == ("shell", "ssh", "apps")


def test_resolve_sections_returns_all_when_none_requested() -> None:
    sections = module.resolve_sections(machine=False, shell=False, repos=False, ssh=False, configs=False, apps=False, backup=False)

    assert sections == module.ALL_STATUS_SECTIONS


@pytest.mark.parametrize(("section", "handler_name"), [("configs", "_run_configs_section"), ("backup", "_run_backup_section")])
def test_run_section_dispatches_to_handler(monkeypatch: pytest.MonkeyPatch, section: module.StatusSection, handler_name: str) -> None:
    calls: list[str] = []

    def fake_handler() -> None:
        calls.append(handler_name)

    monkeypatch.setattr(module, handler_name, fake_handler)

    module._run_section(section=section)

    assert calls == [handler_name]


def test_main_renders_header_then_sections_then_footer(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_display_report_header() -> None:
        calls.append("header")

    def fake_run_section(section: module.StatusSection) -> None:
        calls.append(section)

    def fake_display_report_footer() -> None:
        calls.append("footer")

    monkeypatch.setattr(module, "display_report_header", fake_display_report_header)
    monkeypatch.setattr(module, "_run_section", fake_run_section)
    monkeypatch.setattr(module, "display_report_footer", fake_display_report_footer)

    module.main(sections=("system", "apps"))

    assert calls == ["header", "system", "apps", "footer"]
