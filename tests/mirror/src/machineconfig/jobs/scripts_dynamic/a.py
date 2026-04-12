from __future__ import annotations

from dataclasses import dataclass

import pytest

from machineconfig.jobs.scripts_dynamic import a as analyzer_module


@dataclass(slots=True)
class _FakeCpuFrequency:
    current: float
    max: float


@dataclass(slots=True)
class _FakeVirtualMemory:
    total: int
    available: int
    percent: float


def test_scan_hardware_uses_logical_cores_and_default_frequency_when_probe_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    scanner = analyzer_module.SystemScanner()

    def fake_cpu_count(logical: bool = True) -> int | None:
        return 8 if logical else None

    def fake_cpu_frequency() -> _FakeCpuFrequency:
        raise RuntimeError("cpu frequency unavailable")

    def fake_virtual_memory() -> _FakeVirtualMemory:
        total_ram_bytes = 32 * analyzer_module.BYTES_PER_GB
        available_ram_bytes = 24 * analyzer_module.BYTES_PER_GB
        return _FakeVirtualMemory(total=total_ram_bytes, available=available_ram_bytes, percent=25.0)

    monkeypatch.setattr(analyzer_module.psutil, "cpu_count", fake_cpu_count)
    monkeypatch.setattr(analyzer_module.psutil, "cpu_freq", fake_cpu_frequency)
    monkeypatch.setattr(analyzer_module.psutil, "virtual_memory", fake_virtual_memory)
    monkeypatch.setattr(analyzer_module.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(analyzer_module.SystemScanner, "_detect_cpu_model", staticmethod(lambda: "Fake CPU"))

    scanner.scan_hardware()

    assert scanner.specs.physical_cores == 8
    assert scanner.specs.logical_cores == 8
    assert scanner.specs.max_freq_mhz == analyzer_module.DEFAULT_FREQ_MHZ
    assert scanner.specs.current_freq_mhz == analyzer_module.DEFAULT_FREQ_MHZ
    assert scanner.specs.total_ram_bytes == 32 * analyzer_module.BYTES_PER_GB
    assert scanner.specs.available_ram_bytes == 24 * analyzer_module.BYTES_PER_GB
    assert scanner.specs.ram_percent_used == 25.0
    assert scanner.specs.architecture == "x86_64"
    assert scanner.specs.cpu_model == "Fake CPU"


def test_calculate_metrics_computes_expected_scores_and_tier() -> None:
    scanner = analyzer_module.SystemScanner(
        specs=analyzer_module.HardwareSpecs(
            physical_cores=8,
            logical_cores=16,
            max_freq_mhz=4200.0,
            current_freq_mhz=3900.0,
            total_ram_bytes=64 * analyzer_module.BYTES_PER_GB,
            available_ram_bytes=48 * analyzer_module.BYTES_PER_GB,
            ram_percent_used=25.0,
            architecture="x86_64",
            cpu_model="Fake CPU",
        )
    )

    scanner.calculate_metrics()

    assert scanner.metrics.core_score == pytest.approx(1040.0)
    assert scanner.metrics.freq_multiplier == pytest.approx(1.68)
    assert scanner.metrics.ram_score == pytest.approx(320.0)
    assert scanner.metrics.compute_index == 2067
    assert scanner.metrics.theoretical_gflops == pytest.approx(537.6)
    assert scanner.metrics.tier_name == "HIGH-PERFORMANCE"
    assert scanner.metrics.tier_style == "magenta"
