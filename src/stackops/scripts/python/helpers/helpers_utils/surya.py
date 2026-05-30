from pathlib import Path
from typing import Literal, TypeAlias


SuryaTask: TypeAlias = Literal["ocr", "detect", "layout", "table"]

_SURYA_COMMAND_BY_TASK: dict[SuryaTask, str] = {
    "ocr": "surya_ocr",
    "detect": "surya_detect",
    "layout": "surya_layout",
    "table": "surya_table",
}


def _uv_executable() -> str:
    import platform
    import shutil

    uv_name = "uv.exe" if platform.system() == "Windows" else "uv"
    user_uv_path = Path.home() / ".local" / "bin" / uv_name
    if user_uv_path.exists():
        return str(user_uv_path)

    uv_from_path = shutil.which("uv")
    if uv_from_path is not None:
        return uv_from_path

    return "uv"


def build_surya_command(
    *,
    data_path: str,
    task: SuryaTask,
    output_dir: str | None,
    page_range: str | None,
    images: bool,
    debug: bool,
    keep_server: bool,
    skip_table_detection: bool,
    package_spec: str,
    extra_args: list[str],
    uv_executable: str | None = None,
) -> list[str]:
    command = [
        uv_executable if uv_executable is not None else _uv_executable(),
        "run",
        "--no-project",
        "--with",
        package_spec,
        _SURYA_COMMAND_BY_TASK[task],
        data_path,
    ]

    if output_dir is not None:
        command.extend(["--output_dir", output_dir])
    if page_range is not None:
        command.extend(["--page_range", page_range])
    if images:
        command.append("--images")
    if debug:
        command.append("--debug")
    if keep_server:
        command.append("--keep_server")
    if skip_table_detection:
        command.append("--skip_table_detection")

    command.extend(extra_args)
    return command


def run_surya(
    *,
    data_path: str,
    task: SuryaTask,
    output_dir: str | None,
    page_range: str | None,
    images: bool,
    debug: bool,
    keep_server: bool,
    skip_table_detection: bool,
    package_spec: str,
    extra_args: list[str],
) -> int:
    import subprocess

    command = build_surya_command(
        data_path=data_path,
        task=task,
        output_dir=output_dir,
        page_range=page_range,
        images=images,
        debug=debug,
        keep_server=keep_server,
        skip_table_detection=skip_table_detection,
        package_spec=package_spec,
        extra_args=extra_args,
    )
    return subprocess.run(command, check=False).returncode
