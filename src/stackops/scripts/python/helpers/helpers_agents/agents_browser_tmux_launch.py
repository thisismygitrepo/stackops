from collections.abc import Sequence
from pathlib import Path
import os
import re
import shlex
import subprocess

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import BrowserName
from stackops.scripts.python.helpers.helpers_agents.agents_browser_tmux_common import (
    raise_tmux_command_failure,
    require_tmux,
    run_optional_tmux_command,
    run_required_tmux_command,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_tmux_models import (
    STACKOPS_BROWSER_TMUX_SESSION_NAME,
    BrowserTmuxLaunch,
    BrowserTmuxMetadata,
)


def launch_browser_tmux(
    *,
    browser: BrowserName,
    profile_name: str | None,
    profile_path: Path | None,
    port: int,
    browser_port: int,
    host: str,
    lan: bool,
    browser_command: Sequence[str],
    relay_command: Sequence[str] | None,
    prompt_path: Path,
) -> BrowserTmuxLaunch:
    require_tmux()
    launch_id = _launch_id(browser=browser, profile_name=profile_name, profile_path=profile_path, port=port)
    browser_window_name = _allocate_window_name(base_window_name=f"{launch_id}-endpoint")
    _start_window_command(window_name=browser_window_name, command=browser_command, label="StackOps browser endpoint")
    _set_window_metadata(
        window_name=browser_window_name,
        metadata=BrowserTmuxMetadata(
            launch_id=launch_id,
            role="endpoint",
            browser=browser,
            profile=_profile_label(profile_name=profile_name, profile_path=profile_path, port=port),
            profile_path="-" if profile_path is None else str(profile_path),
            host=host,
            port=str(port),
            browser_port=str(browser_port),
            lan="yes" if lan else "no",
            prompt_path=str(prompt_path),
        ),
    )
    relay_window_name = _start_relay_window(launch_id=launch_id, relay_command=relay_command)
    if relay_window_name is not None:
        _set_window_metadata(
            window_name=relay_window_name,
            metadata=BrowserTmuxMetadata(
                launch_id=launch_id,
                role="relay",
                browser=browser,
                profile=_profile_label(profile_name=profile_name, profile_path=profile_path, port=port),
                profile_path="-" if profile_path is None else str(profile_path),
                host=host,
                port=str(port),
                browser_port=str(browser_port),
                lan="yes" if lan else "no",
                prompt_path=str(prompt_path),
            ),
        )
    return BrowserTmuxLaunch(
        session_name=STACKOPS_BROWSER_TMUX_SESSION_NAME,
        browser_window_name=browser_window_name,
        relay_window_name=relay_window_name,
        attach_command=build_attach_or_switch_command(session_name=STACKOPS_BROWSER_TMUX_SESSION_NAME),
    )


def build_attach_or_switch_command(*, session_name: str) -> tuple[str, ...]:
    if os.environ.get("TMUX"):
        return ("tmux", "switch-client", "-t", session_name)
    return ("tmux", "attach-session", "-t", session_name)


def attach_or_switch_tmux_session(*, session_name: str) -> None:
    command = build_attach_or_switch_command(session_name=session_name)
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"""tmux attach/switch failed with exit code {result.returncode}: {shlex.join(command)}""")


def _launch_id(*, browser: BrowserName, profile_name: str | None, profile_path: Path | None, port: int) -> str:
    profile_label = _profile_label(profile_name=profile_name, profile_path=profile_path, port=port)
    return f"{_slug(value=browser)}-{_slug(value=profile_label)}-p{port}"


def _profile_label(*, profile_name: str | None, profile_path: Path | None, port: int) -> str:
    if profile_name is not None:
        return f"profile-{profile_name}"
    if profile_path is None:
        return "no-profile"
    return f"temp-port-{port}"


def _slug(*, value: str) -> str:
    lowered_value = value.strip().lower()
    slug = re.sub("[^a-z0-9]+", "-", lowered_value).strip("-")
    if slug == "":
        raise ValueError("tmux name segment must not be empty")
    return slug


def _allocate_window_name(*, base_window_name: str) -> str:
    existing_window_names = _list_browser_window_names()
    if base_window_name not in existing_window_names:
        return base_window_name
    for index in range(2, 1000):
        candidate = f"{base_window_name}-{index}"
        if candidate not in existing_window_names:
            return candidate
    raise RuntimeError(f"""Could not allocate a tmux window name for {base_window_name}""")


def _list_browser_window_names() -> set[str]:
    result = run_optional_tmux_command(command=("tmux", "list-windows", "-t", STACKOPS_BROWSER_TMUX_SESSION_NAME, "-F", "#{window_name}"))
    if result is None:
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def _start_window_command(*, window_name: str, command: Sequence[str], label: str) -> None:
    if _browser_session_exists():
        run_required_tmux_command(command=("tmux", "new-window", "-d", "-t", f"{STACKOPS_BROWSER_TMUX_SESSION_NAME}:", "-n", window_name))
    else:
        result = subprocess.run(("tmux", "new-session", "-d", "-s", STACKOPS_BROWSER_TMUX_SESSION_NAME, "-n", window_name), capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise_tmux_command_failure(command=("tmux", "new-session", "-d", "-s", STACKOPS_BROWSER_TMUX_SESSION_NAME, "-n", window_name), result=result)
    _prepare_window(window_name=window_name)
    _send_window_command(window_name=window_name, command=command, label=label)


def _browser_session_exists() -> bool:
    result = subprocess.run(("tmux", "has-session", "-t", STACKOPS_BROWSER_TMUX_SESSION_NAME), capture_output=True, text=True, check=False)
    if result.returncode == 0:
        return True
    detail = (result.stderr or result.stdout or "").strip().lower()
    if "no server running" in detail or "failed to connect to server" in detail or "can't find session" in detail:
        return False
    raise_tmux_command_failure(command=("tmux", "has-session", "-t", STACKOPS_BROWSER_TMUX_SESSION_NAME), result=result)


def _start_relay_window(*, launch_id: str, relay_command: Sequence[str] | None) -> str | None:
    if relay_command is None:
        return None
    relay_window_name = _allocate_window_name(base_window_name=f"{launch_id}-relay")
    run_required_tmux_command(command=("tmux", "new-window", "-d", "-t", f"{STACKOPS_BROWSER_TMUX_SESSION_NAME}:", "-n", relay_window_name))
    _prepare_window(window_name=relay_window_name)
    _send_window_command(window_name=relay_window_name, command=relay_command, label="StackOps browser LAN relay")
    return relay_window_name


def _prepare_window(*, window_name: str) -> None:
    run_required_tmux_command(command=("tmux", "set-window-option", "-t", _window_target(window_name=window_name), "remain-on-exit", "on"))


def _send_window_command(*, window_name: str, command: Sequence[str], label: str) -> None:
    pane_script = _build_pane_script(command=command, label=label)
    run_required_tmux_command(command=("tmux", "send-keys", "-t", _window_target(window_name=window_name), pane_script, "Enter"))


def _build_pane_script(*, command: Sequence[str], label: str) -> str:
    command_text = shlex.join(command)
    return f"""printf '%s\\n' {shlex.quote(label)} {shlex.quote(command_text)}; exec {command_text}"""


def _set_window_metadata(*, window_name: str, metadata: BrowserTmuxMetadata) -> None:
    for key, value in (
        ("@stackops_browser_launch_id", metadata.launch_id),
        ("@stackops_browser_role", metadata.role),
        ("@stackops_browser", metadata.browser),
        ("@stackops_browser_profile", metadata.profile),
        ("@stackops_browser_profile_path", metadata.profile_path),
        ("@stackops_browser_host", metadata.host),
        ("@stackops_browser_port", metadata.port),
        ("@stackops_browser_browser_port", metadata.browser_port),
        ("@stackops_browser_lan", metadata.lan),
        ("@stackops_browser_prompt_path", metadata.prompt_path),
    ):
        run_required_tmux_command(command=("tmux", "set-window-option", "-q", "-t", _window_target(window_name=window_name), key, value))


def _window_target(*, window_name: str) -> str:
    return f"{STACKOPS_BROWSER_TMUX_SESSION_NAME}:{window_name}"
