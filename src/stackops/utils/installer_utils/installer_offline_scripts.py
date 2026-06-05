from pathlib import Path

from stackops.utils.installer_utils.installer_offline_models import ExportStepResult

UNIX_INSTALL_SCRIPT = """#!/usr/bin/env sh
set -eu

SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
BINS_DIR="$SCRIPT_DIR/binaries"
CONFIGS_DIR="$SCRIPT_DIR/configs"
INSTALL_PATH="${INSTALL_PATH:-$HOME/.local/bin}"
CONFIG_ROOT="${CONFIG_ROOT:-$HOME/.config/stackops}"
UV_HOME="${UV_HOME:-$HOME/.local/share/uv}"
LOCAL_BIN="${LOCAL_BIN:-$HOME/.local/bin}"
UV_BUNDLE_DIR="$SCRIPT_DIR/uv_bundle"
UV_MANIFEST="$UV_BUNDLE_DIR/uv_manifest.env"
UV_LINKS="$UV_BUNDLE_DIR/uv_links.txt"
UV_FALLBACK_LINKS="devops cloud agents terminal fire preview utils seek explore stackops"

if [ -d "$BINS_DIR" ]; then
    mkdir -p "$INSTALL_PATH"
    for src_bin in "$BINS_DIR"/*; do
        bin_name="$(basename "$src_bin")"
        dst_bin="$INSTALL_PATH/$bin_name"
        if [ -f "$dst_bin" ] && { [ "$bin_name" = "uv" ] || [ "$bin_name" = "uvx" ]; }; then
            printf "%s\n" "Skipping $bin_name: already exists at $dst_bin"
            continue
        fi
        cp -f "$src_bin" "$dst_bin"
        chmod +x "$dst_bin" 2>/dev/null || true
    done
else
    printf "%s\n" "Warning: $BINS_DIR not found, skipping binaries"
fi

if [ -d "$CONFIGS_DIR" ]; then
    mkdir -p "$CONFIG_ROOT"
    cp -R -f "$CONFIGS_DIR"/* "$CONFIG_ROOT"/ 2>/dev/null || true
else
    printf "%s\n" "Warning: $CONFIGS_DIR not found, skipping configs"
fi

if [ -f "$UV_MANIFEST" ]; then
    . "$UV_MANIFEST"
    TOOL_SRC="$UV_BUNDLE_DIR/tools/$TOOL_NAME"
    PY_SRC="$UV_BUNDLE_DIR/python/$PYTHON_DIR"
    TOOL_DST="$UV_HOME/tools/$TOOL_NAME"
    PY_DST="$UV_HOME/python/$PYTHON_DIR"
    if [ -d "$TOOL_SRC" ]; then
        mkdir -p "$UV_HOME/tools"
        rm -rf "$TOOL_DST"
        cp -R -f "$TOOL_SRC" "$UV_HOME/tools/"
        chmod -R +x "$TOOL_DST/bin" 2>/dev/null || true
    else
        printf "%s\n" "Warning: $TOOL_SRC not found, skipping uv tool restore"
    fi
    if [ -d "$PY_SRC" ]; then
        mkdir -p "$UV_HOME/python"
        if [ -d "$PY_DST" ]; then
            printf "%s\n" "Skipping uv python: $PY_DST already exists"
        else
            cp -R -f "$PY_SRC" "$UV_HOME/python/"
            chmod -R +x "$PY_DST/bin" 2>/dev/null || true
        fi
    else
        printf "%s\n" "Warning: $PY_SRC not found, skipping uv python restore"
    fi
    if [ -d "$TOOL_DST" ] && [ -d "$PY_DST" ]; then
        if [ -f "$TOOL_DST/pyvenv.cfg" ]; then
            sed -i.bak "s|^home = .*|home = $PY_DST/bin|" "$TOOL_DST/pyvenv.cfg" && rm -f "$TOOL_DST/pyvenv.cfg.bak"
        fi
        if [ -n "${PYTHON_BIN:-}" ] && [ -f "$PY_DST/bin/$PYTHON_BIN" ]; then
            ln -sf "$PY_DST/bin/$PYTHON_BIN" "$TOOL_DST/bin/python"
            ln -sf python "$TOOL_DST/bin/python3"
            ln -sf python "$TOOL_DST/bin/$PYTHON_BIN"
        fi
        for file in "$TOOL_DST/bin"/*; do
            if [ -f "$file" ] && head -n 1 "$file" 2>/dev/null | grep -q python; then
                sed -i.bak "1s|^#!.*|#!$TOOL_DST/bin/python3|" "$file" && rm -f "$file.bak"
            fi
        done
    fi
    if [ -d "$TOOL_DST" ]; then
        mkdir -p "$LOCAL_BIN"
        while IFS= read -r link_name; do
            [ -z "$link_name" ] && continue
            target="$TOOL_DST/bin/$link_name"
            if [ -f "$target" ]; then
                ln -sf "$target" "$LOCAL_BIN/$link_name"
            else
                printf "%s\n" "Warning: $target not found, skipping link"
            fi
        done < "${UV_LINKS:-/dev/null}"
        if [ ! -f "$UV_LINKS" ]; then
            for link_name in $UV_FALLBACK_LINKS; do
                target="$TOOL_DST/bin/$link_name"
                if [ -f "$target" ]; then
                    ln -sf "$target" "$LOCAL_BIN/$link_name"
                fi
            done
        fi
    fi
fi
"""

WINDOWS_INSTALL_SCRIPT = """$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BinariesDir = Join-Path $ScriptDir "binaries"
$ConfigsDir = Join-Path $ScriptDir "configs"
$InstallPath = $(if ($env:INSTALL_PATH) { $env:INSTALL_PATH } else { Join-Path $env:LOCALAPPDATA "Microsoft" "WindowsApps" })
$ConfigRoot = $(if ($env:CONFIG_ROOT) { $env:CONFIG_ROOT } else { Join-Path $env:USERPROFILE ".config" "stackops" })

if (Test-Path $BinariesDir) {
    New-Item -ItemType Directory -Force -Path $InstallPath | Out-Null
    Get-ChildItem -Path $BinariesDir -File | ForEach-Object {
        Copy-Item -Path $_.FullName -Destination $InstallPath -Force
    }
} else {
    Write-Host "Warning: $BinariesDir not found, skipping binaries"
}

if (Test-Path $ConfigsDir) {
    New-Item -ItemType Directory -Force -Path $ConfigRoot | Out-Null
    Copy-Item -Path (Join-Path $ConfigsDir "*") -Destination $ConfigRoot -Recurse -Force
} else {
    Write-Host "Warning: $ConfigsDir not found, skipping configs"
}
"""


def write_install_script(*, res_root: Path, system_name: str) -> ExportStepResult:
    if system_name in {"Linux", "Darwin"}:
        script_path = res_root.joinpath("install.sh")
        script_path.write_text(UNIX_INSTALL_SCRIPT, encoding="utf-8")
        script_path.chmod(0o755)
        return ExportStepResult(label="install script", status="included", detail="created install.sh", output_path=script_path)
    if system_name == "Windows":
        script_path = res_root.joinpath("install.ps1")
        script_path.write_text(WINDOWS_INSTALL_SCRIPT, encoding="utf-8")
        return ExportStepResult(label="install script", status="included", detail="created install.ps1", output_path=script_path)
    return ExportStepResult(label="install script", status="skipped", detail=f"unsupported platform: {system_name}", output_path=None)
