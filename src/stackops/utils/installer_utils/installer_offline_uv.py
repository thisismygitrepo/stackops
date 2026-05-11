import shutil
from pathlib import Path
from typing import Iterable

from stackops.utils.installer_utils import installer_offline_constants as constants
from stackops.utils.installer_utils.installer_offline_models import ExportStepResult


def _read_uv_python_home(*, tool_root: Path) -> Path | None:
    pyvenv_cfg = tool_root.joinpath("pyvenv.cfg")
    if not pyvenv_cfg.exists():
        return None
    for line in pyvenv_cfg.read_text(encoding="utf-8").splitlines():
        if line.startswith("home = "):
            home_path = line.split("=", 1)[1].strip()
            if home_path != "":
                return Path(home_path)
    return None


def _read_uv_python_bin_name(*, tool_root: Path) -> str | None:
    python_link = tool_root.joinpath("bin/python")
    if not python_link.is_symlink():
        return None
    try:
        target = python_link.readlink()
    except OSError:
        return None
    target_path = target if target.is_absolute() else python_link.parent.joinpath(target)
    if target_path.name == "":
        return None
    return target_path.name


def _collect_uv_tool_links(*, install_path: Path, tool_root: Path) -> list[str]:
    if not install_path.exists():
        return []
    tool_root_resolved = tool_root.resolve()
    links: list[str] = []
    for entry in install_path.iterdir():
        if not entry.is_symlink():
            continue
        try:
            target = entry.readlink()
        except OSError:
            continue
        target_path = target if target.is_absolute() else entry.parent.joinpath(target)
        try:
            resolved = target_path.resolve()
        except OSError:
            resolved = target_path
        if str(resolved).startswith(str(tool_root_resolved)):
            links.append(entry.name)
    return sorted(set(links))


def _write_uv_manifest(*, bundle_root: Path, python_dir: str, python_bin: str, link_names: Iterable[str]) -> None:
    bundle_root.mkdir(parents=True, exist_ok=True)
    bundle_root.joinpath("uv_manifest.env").write_text(
        f"""TOOL_NAME={constants.UV_TOOL_NAME}
PYTHON_DIR={python_dir}
PYTHON_BIN={python_bin}
""",
        encoding="utf-8",
    )
    bundle_root.joinpath("uv_links.txt").write_text("\n".join(link_names) + "\n", encoding="utf-8")


def _resolve_uv_links(*, install_path: Path, tool_root: Path) -> list[str]:
    links = _collect_uv_tool_links(install_path=install_path, tool_root=tool_root)
    if len(links) > 0:
        return links
    fallback_links = [name for name in constants.UV_TOOL_BINARIES if tool_root.joinpath("bin", name).exists()]
    if tool_root.joinpath("bin", constants.UV_TOOL_NAME).exists():
        fallback_links.append(constants.UV_TOOL_NAME)
    return fallback_links


def export_uv_bundle(*, res_root: Path, install_path: Path, include_uv_bundle: bool, system_name: str) -> ExportStepResult:
    if not include_uv_bundle:
        return ExportStepResult(label="uv bundle", status="skipped", detail="disabled by CLI option", output_path=None)
    if system_name not in {"Linux", "Darwin"}:
        return ExportStepResult(label="uv bundle", status="skipped", detail=f"not exported on {system_name}", output_path=None)
    tool_root = constants.UV_TOOLS_ROOT.joinpath(constants.UV_TOOL_NAME)
    if not tool_root.exists():
        return ExportStepResult(label="uv bundle", status="missing", detail=f"missing tool root: {tool_root}", output_path=None)
    python_home = _read_uv_python_home(tool_root=tool_root)
    python_bin = _read_uv_python_bin_name(tool_root=tool_root)
    if python_home is None or python_bin is None:
        return ExportStepResult(label="uv bundle", status="missing", detail=f"missing python metadata in {tool_root}", output_path=None)
    python_root = python_home.parent
    if not python_root.exists():
        return ExportStepResult(label="uv bundle", status="missing", detail=f"missing python root: {python_root}", output_path=None)
    bundle_root = res_root.joinpath("uv_bundle")
    links = _resolve_uv_links(install_path=install_path, tool_root=tool_root)
    shutil.copytree(tool_root, bundle_root.joinpath("tools", constants.UV_TOOL_NAME), symlinks=True)
    shutil.copytree(python_root, bundle_root.joinpath("python", python_root.name), symlinks=True)
    _write_uv_manifest(
        bundle_root=bundle_root,
        python_dir=python_root.name,
        python_bin=python_bin,
        link_names=links,
    )
    return ExportStepResult(
        label="uv bundle",
        status="included",
        detail=f"copied tool runtime and {len(links)} launcher links",
        output_path=bundle_root,
    )
