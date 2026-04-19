

from pathlib import Path
from subprocess import CompletedProcess

from stackops.scripts.python.helpers.helpers_sessions import _zellij_backend_preview as preview_backend


def _completed_process(stdout: str, returncode: int, stderr: str) -> CompletedProcess[str]:
    return CompletedProcess(args=["zellij"], returncode=returncode, stdout=stdout, stderr=stderr)


def test_session_helpers_strip_state_flags() -> None:
    def fake_strip_ansi_codes(text: str) -> str:
        return text.replace("\u001b[31m", "").replace("\u001b[0m", "")

    raw_exited = "\u001b[31mproj [Created just-now] EXITED\u001b[0m"
    raw_current = "proj [Created earlier] (current)"

    assert preview_backend.session_name(raw_exited, fake_strip_ansi_codes) == "proj"
    assert preview_backend.session_is_exited(raw_exited, fake_strip_ansi_codes)
    assert preview_backend.session_is_current(raw_current, fake_strip_ansi_codes)
    assert preview_backend.session_sort_key("active", lambda text: [text], fake_strip_ansi_codes)[0] is False
    assert preview_backend.session_sort_key("archived EXITED", lambda text: [text], fake_strip_ansi_codes)[0] is True


def test_build_preview_prefers_live_layout_summary() -> None:
    def fake_run_command(args: list[str]) -> CompletedProcess[str]:
        assert args == ["zellij", "--session", "proj", "action", "dump-layout"]
        return _completed_process(stdout='tab name="Main"\n', returncode=0, stderr="")

    def fail_path_lookup(session_name: str) -> Path | None:
        raise AssertionError(f"unexpected path lookup for {session_name}")

    def fail_metadata(session_name: str) -> tuple[list[dict[str, object]], list[dict[str, object]]] | None:
        raise AssertionError(f"unexpected metadata lookup for {session_name}")

    def fail_metadata_summary(tabs: list[dict[str, object]], panes: list[dict[str, object]]) -> str | None:
        raise AssertionError(f"unexpected metadata summary for {tabs}, {panes}")

    def fail_live_tabs(session_name: str) -> list[str]:
        raise AssertionError(f"unexpected tab lookup for {session_name}")

    preview = preview_backend.build_preview(
        raw_line="proj [Created just-now]",
        run_command_fn=fake_run_command,
        strip_ansi_codes_fn=lambda text: text,
        summarize_layout_fn=lambda _layout_text: "tabs: 1",
        find_latest_session_file_fn=fail_path_lookup,
        read_session_metadata_fn=fail_metadata,
        build_metadata_summary_fn=fail_metadata_summary,
        get_live_tab_names_fn=fail_live_tabs,
    )

    assert "preview: live layout" in preview
    assert "tabs: 1" in preview


def test_build_preview_uses_serialized_metadata_summary(tmp_path: Path) -> None:
    session_file = tmp_path / "session-metadata.kdl"
    session_file.write_text("serialized metadata", encoding="utf-8")

    preview = preview_backend.build_preview(
        raw_line="proj [Created earlier]",
        run_command_fn=lambda _args: _completed_process(stdout="", returncode=1, stderr="layout unavailable"),
        strip_ansi_codes_fn=lambda text: text,
        summarize_layout_fn=lambda _layout_text: None,
        find_latest_session_file_fn=lambda _session_name: session_file,
        read_session_metadata_fn=lambda _session_name: ([{"name": "Main"}], [{"id": 1}]),
        build_metadata_summary_fn=lambda _tabs, _panes: "metadata summary",
        get_live_tab_names_fn=lambda _session_name: [],
    )

    assert "preview: serialized metadata" in preview
    assert "metadata summary" in preview


def test_build_preview_falls_back_to_live_tab_list() -> None:
    preview = preview_backend.build_preview(
        raw_line="proj [Created earlier]",
        run_command_fn=lambda _args: _completed_process(stdout="", returncode=1, stderr="layout unavailable"),
        strip_ansi_codes_fn=lambda text: text,
        summarize_layout_fn=lambda _layout_text: None,
        find_latest_session_file_fn=lambda _session_name: None,
        read_session_metadata_fn=lambda _session_name: None,
        build_metadata_summary_fn=lambda _tabs, _panes: None,
        get_live_tab_names_fn=lambda _session_name: ["Main", "Logs"],
    )

    assert "preview: live tab list" in preview
    assert "tabs: 2" in preview
    assert "- Main" in preview
    assert "- Logs" in preview


def test_build_preview_returns_error_text_when_no_preview_source_exists() -> None:
    preview = preview_backend.build_preview(
        raw_line="proj [Created earlier]",
        run_command_fn=lambda _args: _completed_process(stdout="", returncode=1, stderr="boom"),
        strip_ansi_codes_fn=lambda text: text,
        summarize_layout_fn=lambda _layout_text: None,
        find_latest_session_file_fn=lambda _session_name: None,
        read_session_metadata_fn=lambda _session_name: None,
        build_metadata_summary_fn=lambda _tabs, _panes: None,
        get_live_tab_names_fn=lambda _session_name: [],
    )

    assert preview.endswith("boom")
