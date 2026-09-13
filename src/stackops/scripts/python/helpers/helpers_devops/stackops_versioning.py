from dataclasses import dataclass
from datetime import date
import re


@dataclass(frozen=True)
class StackOpsCalVer:
    year: int
    month: int
    release: int | None

    def __post_init__(self) -> None:
        if not 0 <= self.year <= 99:
            raise ValueError("StackOps CalVer year must be between 0 and 99.")
        if not 1 <= self.month <= 12:
            raise ValueError("StackOps CalVer month must be between 1 and 12.")
        if self.release is not None and self.release < 1:
            raise ValueError("StackOps CalVer release number must be positive when present.")


def parse_stackops_calver(version: str) -> StackOpsCalVer:
    if re.fullmatch(r"(?:0|[1-9][0-9]?)\.(?:[1-9]|1[0-2])(?:\.[1-9][0-9]*)?", version) is None:
        raise ValueError(f"Invalid StackOps CalVer: {version!r}. Expected YY.M or YY.M.RELEASE.")
    parts = tuple(int(part) for part in version.split("."))
    return StackOpsCalVer(year=parts[0], month=parts[1], release=parts[2] if len(parts) == 3 else None)


def format_stackops_calver(version: StackOpsCalVer) -> str:
    base_version = f"{version.year}.{version.month}"
    if version.release is None:
        return base_version
    return f"{base_version}.{version.release}"


def get_next_stackops_version(current_version: str, today: date) -> str:
    current = parse_stackops_calver(version=current_version)
    current_month = (current.year, current.month)
    release_month = (today.year % 100, today.month)
    if current_month > release_month:
        raise ValueError(f"Current StackOps version {current_version} is later than today's release month {release_month[0]}.{release_month[1]}.")
    release = None if current_month < release_month else (current.release or 0) + 1
    return format_stackops_calver(StackOpsCalVer(year=release_month[0], month=release_month[1], release=release))
