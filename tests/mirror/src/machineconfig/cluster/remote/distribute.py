from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

from machineconfig.cluster.remote.distribute import (
    Cluster,
    LoadCriterion,
    MachineLoadCalculator,
    MachineSpecs,
    ThreadLoadCalculator,
)
from machineconfig.cluster.remote.models import RemoteMachineConfig, WorkloadParams


def test_thread_load_calculator_scales_by_selected_metric() -> None:
    reference = MachineSpecs(
        cpu=8.0,
        ram=32.0,
        product=256.0,
        cpu_norm=0.5,
        ram_norm=0.5,
        product_norm=0.5,
    )
    candidate = MachineSpecs(
        cpu=4.0,
        ram=16.0,
        product=64.0,
        cpu_norm=0.25,
        ram_norm=0.25,
        product_norm=0.25,
    )
    calculator = ThreadLoadCalculator(
        num_jobs=8,
        load_criterion=LoadCriterion.cpu_norm,
        reference_specs=reference,
    )

    assert calculator.get_num_threads(candidate) == 4


def test_machine_load_calculator_assigns_final_remainder_to_last_machine() -> None:
    calculator = MachineLoadCalculator(max_num=10, load_criterion=LoadCriterion.cpu_norm)
    machines_specs = [
        MachineSpecs(
            cpu=8.0,
            ram=32.0,
            product=256.0,
            cpu_norm=0.6,
            ram_norm=0.6,
            product_norm=0.6,
        ),
        MachineSpecs(
            cpu=4.0,
            ram=16.0,
            product=64.0,
            cpu_norm=0.4,
            ram_norm=0.4,
            product_norm=0.4,
        ),
    ]

    result = calculator.get_workload_params(machines_specs=machines_specs, threads_per_machine=[2, 1])

    assert [(item.idx_start, item.idx_end, item.jobs) for item in result] == [(0, 6, 2), (6, 10, 1)]
    assert calculator.load_ratios == [0.6, 0.4]


def test_cluster_save_and_load_round_trip(tmp_path: Path) -> None:
    cluster = Cluster.__new__(Cluster)
    cluster.job_id = "job-123"
    cluster.root_dir = tmp_path / f"job_id__{cluster.job_id}"
    cluster.results_downloaded = True
    cluster.description = "demo cluster"
    func_kwargs: dict[str, object] = {"threshold": 3}
    cluster.func_kwargs = func_kwargs
    cluster.func = None
    cluster.ssh_connections = []
    cluster.config = RemoteMachineConfig(job_id="job-123", base_dir=str(tmp_path), description="demo cluster")
    cluster.machines_specs = [
        MachineSpecs(
            cpu=8.0,
            ram=32.0,
            product=256.0,
            cpu_norm=0.6,
            ram_norm=0.7,
            product_norm=0.65,
        )
    ]
    cluster.threads_per_machine = [4]
    cluster.workload_params = [
        WorkloadParams(
            idx_min=0,
            idx_max=10,
            idx_start=0,
            idx_end=10,
            idx=0,
            jobs=4,
            job_id="",
        )
    ]
    cluster.machines = []
    cluster.thread_load_calc = ThreadLoadCalculator(
        num_jobs=4,
        load_criterion=LoadCriterion.cpu,
        reference_specs=MachineSpecs(
            cpu=8.0,
            ram=32.0,
            product=256.0,
            cpu_norm=1.0,
            ram_norm=1.0,
            product_norm=1.0,
        ),
    )
    cluster.machine_load_calc = MachineLoadCalculator(max_num=10, load_criterion=LoadCriterion.cpu_norm)
    cluster.machine_load_calc.load_ratios = [0.6]

    save_method = cast(Callable[[], Path], getattr(cluster, "_save"))
    saved_path = save_method()
    loaded = Cluster.load(job_id=cluster.job_id, base_dir=str(tmp_path))

    assert saved_path == cluster.root_dir / "cluster.json"
    assert saved_path.exists()
    assert loaded.root_dir == cluster.root_dir
    assert loaded.results_downloaded is True
    assert loaded.func is None
    assert loaded.func_kwargs == {"threshold": 3}
    assert loaded.config.description == "demo cluster"
    assert loaded.threads_per_machine == [4]
    assert loaded.workload_params[0].idx_end == 10
    assert loaded.machines_specs[0].cpu_norm == 0.6
    assert loaded.machine_load_calc.load_ratios == [0.6]
