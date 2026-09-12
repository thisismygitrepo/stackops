from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.paths import permitted_resource_path
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.sources import json_hook_sources
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgentDefinition, DoctorContext, DoctorResource


def collect_agent_resources(*, definition: DoctorAgentDefinition, context: DoctorContext) -> tuple[DoctorResource, ...]:
    resources = list(definition.collector(context=context))
    configuration_paths = {resource.path for resource in resources if resource.kind == "configuration"}
    sources, _diagnostics = json_hook_sources(agent=definition.agent, context=context)
    for source in sources:
        if source.path in configuration_paths or not permitted_resource_path(path=source.path, home_directory=context.home_directory):
            continue
        if source.path.is_file():
            resources.append(DoctorResource(
                kind="configuration", is_mcp=False, name=source.path.name, origin=source.origin,
                state="configured", path=source.path, detail="Agent settings or hook configuration",
            ))
            configuration_paths.add(source.path)
    if definition.agent in ("codex", "pi", "omp", "opencode"):
        from stackops.scripts.python.helpers.helpers_agents.agents_doctor.extra_configuration import extended_configuration_resources

        resources.extend(resource for resource in extended_configuration_resources(agent=definition.agent, context=context) if resource.path not in configuration_paths)
    return tuple(resources)
