from pathlib import Path
from subprocess import CompletedProcess

import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_skill_impl
from stackops.utils import code as code_utils


def test_run_agent_skill_install_commands_returns_shell_exit_code(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("OP_PROGRAM_PATH", raising=False)
    captured: dict[str, object] = {}

    def fake_run_shell_script(*, script: str, display_script: bool, clean_env: bool) -> CompletedProcess[bytes]:
        captured["script"] = script
        captured["display_script"] = display_script
        captured["clean_env"] = clean_env
        return CompletedProcess(args=["bash"], returncode=23)

    monkeypatch.setattr(code_utils, "run_shell_script", fake_run_shell_script)

    return_code = agents_skill_impl.run_agent_skill_install_commands(
        install_root=tmp_path,
        commands=(("bunx", "skills@latest", "add", "vercel-labs/agent-browser", "--yes"),),
    )

    assert return_code == 23
    assert captured == {
        "script": f"cd {tmp_path}\nbunx skills@latest add vercel-labs/agent-browser --yes\n",
        "display_script": True,
        "clean_env": False,
    }
