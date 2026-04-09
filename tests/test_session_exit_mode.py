from base64 import b64decode

from machineconfig.cluster.sessions_managers.session_exit_mode import (
    build_powershell_exit_mode_command_parts,
)
from machineconfig.cluster.sessions_managers.windows_terminal.wt_utils.wt_helpers import (
    generate_wt_command_string,
)
from machineconfig.utils.schemas.layouts.layout_types import LayoutConfig


def test_build_powershell_exit_mode_command_parts_terminate_mode_prompts_for_restart_or_close() -> None:
    command_parts = build_powershell_exit_mode_command_parts(
        command="python -c \"print('hi')\"",
        exit_mode="terminate",
        shell_name="pwsh",
    )

    encoded_script = command_parts[-1]
    decoded_script = b64decode(encoded_script).decode("utf-16le")

    assert command_parts[:3] == ["pwsh", "-NoLogo", "-NoProfile"]
    assert "-NoExit" not in command_parts
    assert "Press Enter to restart" in decoded_script
    assert "press Enter to close" in decoded_script
    assert "Invoke-Expression -Command $machineconfigCommand" in decoded_script


def test_generate_wt_command_string_uses_encoded_exit_wrapper() -> None:
    layout: LayoutConfig = {
        "layoutName": "Alpha",
        "layoutTabs": [
            {
                "tabName": "tab-1",
                "startDir": "/tmp",
                "command": "python -c \"print('hello')\"",
            }
        ],
    }

    command_string = generate_wt_command_string(
        layout_config=layout,
        window_name="Alpha",
        exit_mode="killWindow",
    )

    assert "-EncodedCommand" in command_string
    assert "python -c" not in command_string
