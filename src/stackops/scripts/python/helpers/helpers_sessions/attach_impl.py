import re
import shlex
import subprocess
from pathlib import Path
from typing import Literal, TypeAlias, overload

from stackops.utils.cli_utils.command_lookup import check_tool_exists
from stackops.utils.options_utils.options import choose_from_options

NEW_SESSION_LABEL = "NEW SESSION"
KILL_ALL_AND_NEW_LABEL = "KILL ALL SESSIONS & START NEW"
_ANSI_ESCAPE_RE = re.compile(
    r"(?:\x1B|\u001B|\033)\[[0-?]*[ -/]*[@-~]|\[[0-9;?]+[ -/]*[@-~]|\[m"
)

AttachSessionAction: TypeAlias = Literal["error", "handoff_script"]
AttachSessionChoice: TypeAlias = tuple[AttachSessionAction, str]


def strip_ansi_codes(text: str) -> str:
    return _ANSI_ESCAPE_RE.sub("", text)


def natural_sort_key(text: str) -> list[int | str]:
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", text)]


def run_command(args: list[str], timeout: float = 5.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)


def quote(value: str | Path) -> str:
    return shlex.quote(str(value))


@overload
def interactive_choose_with_preview(
    msg: str,
    options_to_preview_mapping: dict[str, str],
    multi: Literal[False] = False,
) -> str | None: ...


@overload
def interactive_choose_with_preview(
    msg: str,
    options_to_preview_mapping: dict[str, str],
    multi: Literal[True],
) -> list[str]: ...


def interactive_choose_with_preview(
    msg: str,
    options_to_preview_mapping: dict[str, str],
    multi: bool = False,
) -> str | list[str] | None:
    if options_to_preview_mapping and check_tool_exists("tv"):
        from stackops.utils.options_utils.tv_options import choose_from_dict_with_preview

        try:
            if multi:
                chosen_multi = choose_from_dict_with_preview(
                    options_to_preview_mapping=options_to_preview_mapping,
                    extension="md",
                    multi=True,
                    preview_size_percent=70.0,
                )
                return chosen_multi
            else:
                chosen_single = choose_from_dict_with_preview(
                    options_to_preview_mapping=options_to_preview_mapping,
                    extension="md",
                    multi=False,
                    preview_size_percent=70.0,
                )
                return chosen_single
        except Exception:
            pass

    if multi:
        chosen_multi_options = choose_from_options(
            msg=msg,
            multi=True,
            options=list(options_to_preview_mapping.keys()),
            tv=True,
            custom_input=False,
        )
        return chosen_multi_options or []
    else:
        chosen_single = choose_from_options(
            msg=msg,
            multi=False,
            options=list(options_to_preview_mapping.keys()),
            tv=True,
            custom_input=False,
        )
        return chosen_single


def choose_session(
    backend: Literal["tmux", "herdr"],
    name: str | None,
    new_session: bool,
    kill_all: bool,
    window: bool = False,
) -> AttachSessionChoice:
    match backend:
        case "tmux":
            from stackops.scripts.python.helpers.helpers_sessions._tmux_backend import choose_session as _tmux

            return _tmux(name=name, new_session=new_session, kill_all=kill_all, window=window)
        case "herdr":
            from stackops.scripts.python.helpers.helpers_sessions._herdr_backend import choose_session as _herdr

            return _herdr(name=name, new_session=new_session, kill_all=kill_all, window=window)
    raise ValueError(f"Unsupported backend: {backend}")


def get_session_tabs() -> list[tuple[str, str]]:
    from stackops.scripts.python.helpers.helpers_sessions._tmux_backend import run_command

    result = run_command(["tmux", "list-windows", "-a", "-F", "#S\t#W"])
    if result.returncode != 0:
        return []
    session_tabs: list[tuple[str, str]] = []
    for line in result.stdout.splitlines():
        session_name, separator, window_name = line.partition("\t")
        if separator == "" or session_name == "" or window_name == "":
            continue
        session_tabs.append((session_name, window_name))
    return session_tabs
