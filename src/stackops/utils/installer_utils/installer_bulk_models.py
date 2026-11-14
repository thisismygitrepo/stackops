from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Literal

from stackops.utils.schemas.installer.installer_types import InstallRequest, InstallationResult, InstallerData


type BulkInstallStatus = Literal["installed", "updated", "unchanged", "skipped", "failed"]


@dataclass(frozen=True, slots=True)
class BulkInstallJob:
    installer_data: InstallerData
    install_request: InstallRequest


@dataclass(frozen=True, slots=True)
class BulkInstallOutcome:
    result: InstallationResult


@dataclass(frozen=True, slots=True)
class PlannedInstall:
    installer_data: InstallerData
    exe_name: str
    holds_system_installer_lock: bool
    may_need_sudo: bool
    was_installed: bool
    skip: bool


@dataclass(frozen=True, slots=True)
class RunningInstall:
    planned: PlannedInstall
    process: subprocess.Popen[bytes]
    started_at: float
    log_path: Path
    outcome_path: Path


@dataclass(frozen=True, slots=True)
class FinishedInstall:
    planned: PlannedInstall
    result: InstallationResult
    seconds: float
    log_path: Path | None
