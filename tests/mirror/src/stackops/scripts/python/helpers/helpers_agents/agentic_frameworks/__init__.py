from importlib import import_module


def test_fire_crush_path_reference_constant() -> None:
    module = import_module("stackops.scripts.python.helpers.helpers_agents.agentic_frameworks")
    assert module.FIRE_CRUSH_PATH_REFERENCE == "fire_crush.json"
