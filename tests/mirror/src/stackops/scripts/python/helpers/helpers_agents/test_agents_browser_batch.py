from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_browser_batch


def test_build_browser_profile_launch_specs_maps_numbered_profiles_and_uses_free_ports_for_other_names(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profiles_root = tmp_path.joinpath("browsers-profiles")
    chrome_root = profiles_root.joinpath("chrome")
    for profile_name in ("p10", "work", "p2", "p1"):
        chrome_root.joinpath(profile_name).mkdir(parents=True)
    chrome_root.joinpath("ignored.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(agents_browser_batch, "BROWSER_PROFILES_ROOT", profiles_root)

    specs = agents_browser_batch.build_browser_profile_launch_specs(browser="chrome")

    assert [(spec.profile_name, spec.port) for spec in specs] == [("p1", 60001), ("p2", 60002), ("work", 60003), ("p10", 60010)]


def test_build_browser_profile_launch_specs_requires_at_least_one_profile(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    profiles_root = tmp_path.joinpath("browsers-profiles")
    profiles_root.joinpath("firefox").mkdir(parents=True)
    monkeypatch.setattr(agents_browser_batch, "BROWSER_PROFILES_ROOT", profiles_root)

    with pytest.raises(RuntimeError, match="No browser profiles found"):
        agents_browser_batch.build_browser_profile_launch_specs(browser="firefox")


def test_build_browser_profile_launch_specs_applies_custom_port_start(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    profiles_root = tmp_path.joinpath("browsers-profiles")
    profiles_root.joinpath("brave", "p1").mkdir(parents=True)
    profiles_root.joinpath("brave", "p2").mkdir()
    monkeypatch.setattr(agents_browser_batch, "BROWSER_PROFILES_ROOT", profiles_root)

    specs = agents_browser_batch.build_browser_profile_launch_specs(browser="brave", port_start=61000)

    assert [(spec.profile_name, spec.port) for spec in specs] == [("p1", 61001), ("p2", 61002)]
