import json

import pytest

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_apply import apply_cleanup_plan
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_plan import build_cleanup_plan
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_resources import collect_cleanup_resources
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgent, DoctorContext
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.registry import DOCTOR_DEFINITION_BY_AGENT


@pytest.mark.parametrize("agent", ("omp", "opencode"))
def test_full_reset_removes_custom_skill_registration_preserves_external_source(hook_context: DoctorContext, agent: DoctorAgent) -> None:
    external = hook_context.home_directory / "external-skills"
    original = external / "custom" / "SKILL.md"
    original.parent.mkdir(parents=True)
    original.write_text("---\nname: external-skill\n---\nOriginal external instructions")
    config_root = hook_context.omp_home if agent == "omp" else hook_context.xdg_config_directory / "opencode"
    config_root.mkdir(parents=True)
    if agent == "omp":
        config = config_root / "settings.json"
        config.write_text(json.dumps({"skills": {"customDirectories": [str(external)]}}))
    else:
        config = config_root / "opencode.json"
        config.write_text(json.dumps({"skills": [str(external)]}))
    direct = config_root / "skills" / "native" / "SKILL.md"
    direct.parent.mkdir(parents=True)
    direct.write_text("---\nname: native-skill\n---\nNative instructions")
    resources = DOCTOR_DEFINITION_BY_AGENT[agent].collector(context=hook_context)
    assert next(resource.state for resource in resources if resource.path == original) == "referenced"
    assert next(resource.state for resource in resources if resource.path == direct) == "available"

    inventory = collect_cleanup_resources(agent=agent, context=hook_context, resource_focuses=("all",))
    plan = build_cleanup_plan(inventory=inventory, scope="global", match=None, home_directory=hook_context.home_directory)
    assert not plan.blockers
    apply_cleanup_plan(plan=plan, backup_root=hook_context.home_directory / "backups", home_directory=hook_context.home_directory)
    assert original.read_text() == "---\nname: external-skill\n---\nOriginal external instructions"
    assert not config.exists()
    assert not direct.exists()


def test_omp_full_reset_preserves_skills_inside_external_extension_package(hook_context: DoctorContext) -> None:
    external = hook_context.home_directory / "external-package"
    original = external / "skills" / "custom" / "SKILL.md"
    original.parent.mkdir(parents=True)
    original.write_text("---\nname: package-skill\n---\nPackage-owned instructions")
    (external / "index.ts").write_text("export default function(pi) {}")
    (external / "package.json").write_text('{"omp":{"extensions":["./index.ts"]}}')
    hook_context.omp_home.mkdir(parents=True)
    config = hook_context.omp_home / "settings.json"
    config.write_text(json.dumps({"extensions": [str(external)]}))
    resources = DOCTOR_DEFINITION_BY_AGENT["omp"].collector(context=hook_context)
    assert next(resource.state for resource in resources if resource.path == original) == "referenced"

    inventory = collect_cleanup_resources(agent="omp", context=hook_context, resource_focuses=("all",))
    plan = build_cleanup_plan(inventory=inventory, scope="global", match=None, home_directory=hook_context.home_directory)
    assert not plan.blockers
    apply_cleanup_plan(plan=plan, backup_root=hook_context.home_directory / "backups", home_directory=hook_context.home_directory)
    assert original.read_text() == "---\nname: package-skill\n---\nPackage-owned instructions"
    assert (external / "index.ts").exists()
    assert (external / "package.json").exists()
    assert not config.exists()
