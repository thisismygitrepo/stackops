from __future__ import annotations

import shlex
from pathlib import Path

from stackops.scripts.python.helpers.helpers_cloud import cloud_mount_zellij


def test_kdl_escape_escapes_quotes_and_backslashes() -> None:
    value = 'cloud "A" \\ share'

    assert cloud_mount_zellij._kdl_escape(value) == 'cloud \\\"A\\\" \\\\ share'


def test_build_zellij_layout_kdl_focuses_only_first_tab() -> None:
    layout = cloud_mount_zellij._build_zellij_layout_kdl(
        mount_commands={
            "alpha": "rclone mount alpha",
            "beta": "rclone mount beta",
        },
        mount_locations={
            "alpha": r"C:\alpha",
            "beta": "/tmp/beta",
        },
    )

    assert layout.count("focus=true") == 1
    assert 'tab name="alpha" focus=true {' in layout
    assert 'tab name="beta" {' in layout
    assert 'args "C:\\\\alpha"' in layout


def test_build_zellij_launch_command_writes_layout_file() -> None:
    command = cloud_mount_zellij.build_zellij_launch_command(
        mount_commands={"alpha": "rclone mount alpha"},
        mount_locations={"alpha": "/tmp/alpha"},
        session_name="team sync",
    )
    parts = shlex.split(command)
    layout_path = Path(parts[4])

    try:
        assert parts[:4] == [
            "zellij",
            "--session",
            "team sync",
            "--new-session-with-layout",
        ]
        assert layout_path.exists()
        assert 'tab name="alpha" focus=true {' in layout_path.read_text(encoding="utf-8")
    finally:
        layout_path.unlink(missing_ok=True)
