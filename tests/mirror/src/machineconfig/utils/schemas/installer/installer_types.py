from __future__ import annotations

import dataclasses

import pytest

from machineconfig.utils.schemas.installer import installer_types as installer_types_module


@pytest.mark.parametrize(("system_name", "expected"), [("Windows", "windows"), ("Linux", "linux"), ("Darwin", "darwin")])
def test_get_os_name_maps_supported_platform_values(monkeypatch: pytest.MonkeyPatch, system_name: str, expected: str) -> None:
    monkeypatch.setattr(installer_types_module.platform, "system", lambda: system_name)

    assert installer_types_module.get_os_name() == expected


def test_get_os_name_rejects_unknown_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(installer_types_module.platform, "system", lambda: "Plan9")

    with pytest.raises(NotImplementedError, match="Plan9"):
        installer_types_module.get_os_name()


@pytest.mark.parametrize(
    ("machine_name", "expected"), [("x86_64", "amd64"), ("amd64", "amd64"), ("aarch64", "arm64"), ("ARMv8", "arm64"), ("mips64", "amd64")]
)
def test_get_normalized_arch_maps_common_machine_names(monkeypatch: pytest.MonkeyPatch, machine_name: str, expected: str) -> None:
    monkeypatch.setattr(installer_types_module.platform, "machine", lambda: machine_name)

    assert installer_types_module.get_normalized_arch() == expected


def test_install_request_is_frozen_and_slotted() -> None:
    request = installer_types_module.InstallRequest(version="1.2.3", update=True)

    assert not hasattr(request, "__dict__")
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(request, "update", False)
