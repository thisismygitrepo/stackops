"""Generated mock layouts for experimenting with sessions commands."""



import base64
from dataclasses import dataclass
from pathlib import Path
import platform
import shlex
import subprocess
import sys

from stackops.utils.schemas.layouts.layout_types import LayoutConfig, TabConfig


_INLINE_WORKER_SCRIPT = """
import os
import sys
import time

label = sys.argv[1]
steps = int(sys.argv[2])
sleep_seconds = float(sys.argv[3])
payload = int(sys.argv[4])
cwd = os.getcwd()
pid = os.getpid()
running_total = 0
print(
    f"[{label}] pid={pid} cwd={cwd} steps={steps} sleep={sleep_seconds:.2f}s",
    flush=True,
)
for step_number in range(1, steps + 1):
    running_total += payload + (step_number * step_number)
    print(
        f"[{label}] step={step_number}/{steps} total={running_total}",
        flush=True,
    )
    if step_number < steps:
        time.sleep(sleep_seconds)
print(f"[{label}] finished pid={pid} total={running_total}", flush=True)
""".strip()
_INLINE_WORKER_SCRIPT_B64 = base64.b64encode(
    _INLINE_WORKER_SCRIPT.encode("utf-8")
).decode("ascii")
_INLINE_WORKER_CODE = (
    "import base64;"
    f"exec(base64.b64decode('{_INLINE_WORKER_SCRIPT_B64}').decode('utf-8'))"
)


@dataclass(frozen=True, slots=True)
class TestLayoutPlan:
    layout_name: str
    tab_count: int
    base_steps: int
    start_dir: Path
    sleep_pattern: tuple[float, ...]


def _join_command(parts: list[str]) -> str:
    if platform.system().lower() == "windows":
        return subprocess.list2cmdline(parts)
    return shlex.join(parts)


def _build_worker_command(
    python_executable: Path,
    label: str,
    steps: int,
    sleep_seconds: float,
    payload: int,
) -> str:
    return _join_command(
        parts=[
            str(python_executable),
            "-u",
            "-c",
            _INLINE_WORKER_CODE,
            label,
            str(steps),
            f"{sleep_seconds:.2f}",
            str(payload),
        ]
    )


def _build_tabs(
    plan: TestLayoutPlan,
    python_executable: Path,
) -> list[TabConfig]:
    tabs: list[TabConfig] = []
    for tab_index in range(plan.tab_count):
        tab_number = tab_index + 1
        sleep_seconds = plan.sleep_pattern[tab_index % len(plan.sleep_pattern)]
        steps = plan.base_steps + (tab_index % 4)
        payload = 25 + (tab_number * 7) + (plan.base_steps * 5)
        worker_label = f"{plan.layout_name}_{tab_number:02d}"
        tabs.append(
            {
                "tabName": f"{plan.layout_name}-tab-{tab_number:02d}",
                "startDir": str(plan.start_dir),
                "command": _build_worker_command(
                    python_executable=python_executable,
                    label=worker_label,
                    steps=steps,
                    sleep_seconds=sleep_seconds,
                    payload=payload,
                ),
            }
        )
    return tabs


def build_test_layouts(base_dir: Path) -> list[LayoutConfig]:
    base_dir_resolved = base_dir.expanduser().resolve()
    home_dir = Path.home().resolve()
    python_executable = Path(sys.executable).resolve()
    plans = (
        TestLayoutPlan(
            layout_name="test-layout-alpha",
            tab_count=6,
            base_steps=4,
            start_dir=base_dir_resolved,
            sleep_pattern=(0.65, 0.90, 1.15),
        ),
        TestLayoutPlan(
            layout_name="test-layout-beta",
            tab_count=10,
            base_steps=5,
            start_dir=home_dir,
            sleep_pattern=(0.50, 0.80, 1.10, 1.40),
        ),
        TestLayoutPlan(
            layout_name="test-layout-gamma",
            tab_count=14,
            base_steps=4,
            start_dir=base_dir_resolved,
            sleep_pattern=(0.45, 0.70, 0.95, 1.20, 1.45),
        ),
        TestLayoutPlan(
            layout_name="test-layout-delta",
            tab_count=18,
            base_steps=3,
            start_dir=home_dir,
            sleep_pattern=(0.40, 0.60, 0.85, 1.10, 1.35, 1.60),
        ),
    )
    layouts: list[LayoutConfig] = []
    for plan in plans:
        layouts.append(
            {
                "layoutName": plan.layout_name,
                "layoutTabs": _build_tabs(
                    plan=plan,
                    python_executable=python_executable,
                ),
            }
        )
    return layouts


def count_tabs_in_layouts(layouts: list[LayoutConfig]) -> int:
    return sum(len(layout["layoutTabs"]) for layout in layouts)
