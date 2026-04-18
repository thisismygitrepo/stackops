from importlib import import_module
from pathlib import Path
from typing import cast


EXPECTED_EXPORTS = {
    "JOB_STATUS",
    "TRANSFER_METHOD",
    "LAUNCH_METHOD",
    "MACHINE_TYPE",
    "WorkloadParams",
    "JobStatus",
    "EmailParams",
    "LogEntry",
    "RemoteStackOpsConfig",
    "ExecutionTimings",
    "JobParams",
    "FileManager",
    "RemoteMachine",
    "CloudManager",
    "LoadCriterion",
    "MachineSpecs",
    "ThreadLoadCalculator",
    "MachineLoadCalculator",
    "Cluster",
    "FLOWCHART_PATH_REFERENCE",
}


def test_remote_package_exports_names_and_existing_flowchart() -> None:
    module = import_module("stackops.cluster.remote")
    flowchart_path = Path(cast(str, module.__file__)).resolve().parent / module.FLOWCHART_PATH_REFERENCE

    assert set(module.__all__) == EXPECTED_EXPORTS
    for name in EXPECTED_EXPORTS:
        assert hasattr(module, name)
    assert flowchart_path.is_file()
