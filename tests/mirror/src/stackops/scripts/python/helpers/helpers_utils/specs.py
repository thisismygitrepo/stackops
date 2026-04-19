

import subprocess

import pytest

from stackops.scripts.python.helpers.helpers_utils import specs as module


def test_clean_cpu_name_removes_noise() -> None:
    raw_name = "AMD Ryzen(TM) 7 8745HS w/ Radeon 780M Graphics @ 3.80GHz"

    cleaned = module.clean_cpu_name(raw_name)

    assert cleaned == "AMD Ryzen 7 8745HS"


def test_escape_regex_term_escapes_regex_metacharacters() -> None:
    assert module.escape_regex_term("Intel Core i7-13700H (OEM)+") == r"Intel Core i7-13700H \(OEM\)\+"


def test_run_geekbench_lookup_detects_table_rows(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    result = subprocess.CompletedProcess(args=["uvx"], returncode=0, stdout="│ Description │ Single │\n│ AMD Ryzen 7 8745HS │ 2500 │\n", stderr="")
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: result)

    found = module.run_geekbench_lookup(search_term="AMD Ryzen 7 8745HS", display_term="AMD Ryzen 7 8745HS")

    captured = capsys.readouterr()
    assert found is True
    assert 'Running: uvx --from geekbench-browser-python gbr "AMD Ryzen 7 8745HS" --verbose' in captured.out
    assert "2500" in captured.out


def test_run_geekbench_lookup_reports_missing_results(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    result = subprocess.CompletedProcess(args=["uvx"], returncode=0, stdout="debug line\n", stderr="")
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: result)

    found = module.run_geekbench_lookup(search_term="No Match", display_term="No Match")

    captured = capsys.readouterr()
    assert found is False
    assert "Debug output from tool" in captured.out
    assert "No results found for 'No Match'." in captured.out


def test_main_progresses_through_fallback_search_terms(monkeypatch: pytest.MonkeyPatch) -> None:
    attempted_display_terms: list[str] = []

    monkeypatch.setattr(module, "get_cpu_name", lambda: "AMD Ryzen 7 8745HS")
    monkeypatch.setattr(module, "clean_cpu_name", lambda cpu_name: cpu_name)

    def fake_run_geekbench_lookup(search_term: str, display_term: str) -> bool:
        attempted_display_terms.append(display_term)
        return display_term == "AMD Ryzen 7 87.."

    monkeypatch.setattr(module, "run_geekbench_lookup", fake_run_geekbench_lookup)

    module.main()

    assert attempted_display_terms == ["AMD Ryzen 7 8745HS", "AMD Ryzen 7 8745", "AMD Ryzen 7 87.."]


def test_main_exits_early_when_cpu_is_unknown(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(module, "get_cpu_name", lambda: "Unknown CPU")

    module.main()

    captured = capsys.readouterr()
    assert "Could not detect CPU name. Exiting." in captured.out
