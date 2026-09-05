from typing import Final

from stackops.scripts.python.helpers.helpers_agents.agents_skill_impl import (
    AGENT_SKILL_PREVIEW_SIZE_PERCENT,
    build_agent_skill_preview_mapping,
    get_agent_skill_source,
    supported_agent_skill_names,
)

GITHUB_URL_PREFIX: Final[str] = "https://github.com/"


def choose_run_skill_name() -> str:
    from stackops.utils.options_utils import tv_options

    selection = tv_options.choose_from_dict_with_preview(
        options_to_preview_mapping=build_agent_skill_preview_mapping(),
        extension="json",
        multi=False,
        preview_size_percent=AGENT_SKILL_PREVIEW_SIZE_PERCENT,
    )
    if selection is None:
        raise ValueError("Selection cancelled for run-prompt skill")
    return selection


def resolve_run_skill_name(*, skill: str | None) -> str | None:
    match skill:
        case None:
            return None
        case "":
            return choose_run_skill_name()
        case skill_name:
            supported = supported_agent_skill_names()
            if skill_name not in supported:
                raise ValueError(f"Skill '{skill_name}' is not recognized. Supported skills: {', '.join(supported)}")
            return skill_name


def resolve_agent_skill_source_url(*, source: str) -> str:
    if source.startswith(("http://", "https://")):
        return source
    return f"{GITHUB_URL_PREFIX}{source}"


def render_agent_skill_reference(*, skill_name: str) -> str:
    source = get_agent_skill_source(skill_name=skill_name)
    source_url = resolve_agent_skill_source_url(source=source.source)
    lines = [f"Skill name: `{skill_name}`", f"Source repository: {source_url}"]
    if source.skill is not None:
        lines.append(f"Skill directory inside the repository: `{source.skill}`")
    lines.append("")
    lines.append("Read the SKILL.md of this skill from the source repository above, then follow it while handling the prompt.")
    lines.append("Do not install this skill. It is referenced on the fly only.")
    return "\n".join(lines)
