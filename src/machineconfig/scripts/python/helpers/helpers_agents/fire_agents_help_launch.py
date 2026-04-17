import random
import shlex
from pathlib import Path

from machineconfig.scripts.python.helpers.helpers_agents.fire_agents_helper_types import (
    AGENTS,
    AGENT_NAME_FORMATTER,
    HOST,
    PROVIDER,
    AI_SPEC,
    API_SPEC,
)
from machineconfig.scripts.python.helpers.helpers_agents.reasoning_capabilities import ReasoningEffort
from machineconfig.utils.schemas.layouts.layout_types import LayoutConfig, LayoutsFile, TabConfig


JURISDICTION_SUFFIX = r"""

You don't need to do any other work beside the content of this material file.
And be mindful that other agents might be operating at the same time in the same place, and they are assigned other bits of work.
Don't be surprised if you saw progressing changes in other places. We try to minimize conflict that arise from multiple agents working on exact same problem, unaware of each other, so, it shoulnd't happen in 99% of cases.
"""

def _format_material_reference(*, prompt_material_path: Path, repo_root: Path) -> str:
    try:
        return str(prompt_material_path.relative_to(repo_root))
    except ValueError:
        return str(prompt_material_path)


def _build_generic_agent_command(agent: AGENTS, prompt_path: Path, reasoning_effort: ReasoningEffort | None) -> str:
    from machineconfig.scripts.python.helpers.helpers_agents.agents_run_impl import build_agent_command

    return build_agent_command(agent=agent, prompt_file=prompt_path, reasoning_effort=reasoning_effort)


def get_api_keys(provider: PROVIDER, *, silent_if_missing: bool = False) -> list[API_SPEC]:
    from machineconfig.utils.io import read_ini

    api_key_path = Path.home().joinpath(f"dotfiles/creds/llm/{provider}/api_keys.ini")
    res: list[API_SPEC] = []
    if not api_key_path.exists() or not api_key_path.is_file():
        if not silent_if_missing:
            print(f"No API key file found for provider {provider} at expected location: {api_key_path}. Returning empty API key list.")
        return res
    config = read_ini(api_key_path)
    for a_section_name in list(config.sections()):
        a_section = config[a_section_name]
        if "api_key" in a_section:
            api_key = a_section["api_key"].strip()
            if api_key:
                res.append(
                    API_SPEC(
                        api_key=api_key, api_name=a_section.get("api_name", ""), api_label=a_section_name, api_account=a_section.get("email", "")
                    )
                )
    print(f"Found {len(res)} {provider} API keys configured.")
    return res


def prep_agent_launch(
    repo_root: Path,
    agents_dir: Path,
    prompts_material: list[str],
    prompt_prefix: str,
    join_prompt_and_context: bool,
    machine: HOST,
    model: str | None,
    reasoning_effort: ReasoningEffort | None,
    provider: PROVIDER | None,
    agent: AGENTS,
    *,
    job_name: str,
) -> None:
    if agent == "codex":
        if provider is None:
            provider = "openai"
        elif provider != "openai":
            raise ValueError("Codex agent only works with openai provider.")

    agents_dir.mkdir(parents=True, exist_ok=True)
    prompt_folder = agents_dir / "prompts"
    prompt_folder.mkdir(parents=True, exist_ok=True)

    for idx, a_prompt_material in enumerate(prompts_material):
        prompt_root = prompt_folder / f"agent_{idx}"
        prompt_root.mkdir(parents=True, exist_ok=True)
        prompt_path = prompt_root / f"agent_{idx}_prompt.txt"
        if join_prompt_and_context:
            prompt_material_path = prompt_path
            prompt_path.write_text(prompt_prefix + """\nPlease only look at:\n""" + a_prompt_material + JURISDICTION_SUFFIX, encoding="utf-8")
        else:
            prompt_material_path = prompt_root / f"agent_{idx}_material.txt"
            prompt_material_path.write_text(a_prompt_material, encoding="utf-8")
            material_reference = _format_material_reference(prompt_material_path=prompt_material_path, repo_root=repo_root)
            prompt_path.write_text(prompt_prefix + f"""\nPlease only look at:\n{material_reference}.""" + JURISDICTION_SUFFIX, encoding="utf-8",)

        agent_cmd_launch_path = prompt_root / AGENT_NAME_FORMATTER.format(idx=idx)  # e.g., agent_0_cmd.sh
        random_sleep_time = random.uniform(0, 3)
        cmd_prefix = f"""#!/usr/bin/env bash

echo "Using machine: {machine}, model: {model}, reasoning_effort: {reasoning_effort}, provider: {provider}, and agent: {agent}"
echo "{job_name}-{idx} CMD {agent_cmd_launch_path}"
echo "{job_name}-{idx} PROMPT {prompt_path}"
echo "{job_name}-{idx} CONTEXT {prompt_material_path}"

export FIRE_AGENTS_AGENT_NAME="{agent}"
export FIRE_AGENTS_JOB_NAME="{job_name}"
export FIRE_AGENTS_PROMPT_FILE="{prompt_path}"
export FIRE_AGENTS_MATERIAL_FILE="{prompt_material_path}"
export FIRE_AGENTS_AGENT_LAUNCHER="{agent_cmd_launch_path}"


echo "Sleeping for {random_sleep_time:.2f} seconds to stagger agent startups ... Press Ctrl+C to cancel."
sleep {random_sleep_time:.2f}
echo "--------START OF AGENT OUTPUT--------"
sleep 0.1

        """
        ai_spec: AI_SPEC
        match agent:
            case "gemini":
                assert provider == "google", "Gemini agent only works with google provider."
                api_keys = get_api_keys(provider="google")
                api_spec = api_keys[idx % len(api_keys)] if len(api_keys) > 0 else None
                if api_spec is None:
                    raise ValueError("No API keys found for Google Gemini. Please configure them in dotfiles/creds/llm/google/api_keys.ini")
                ai_spec = AI_SPEC(
                    provider=provider,
                    model="gemini-2.5-pro",
                    agent=agent,
                    machine=machine,
                    api_spec=api_spec,
                    reasoning_effort=reasoning_effort,
                )
                from machineconfig.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_gemini import fire_gemini

                cmd = fire_gemini(ai_spec=ai_spec, prompt_path=prompt_path, repo_root=repo_root)
            case "cursor-agent":
                api_spec = API_SPEC(api_key=None, api_name="", api_label="", api_account="")
                ai_spec = AI_SPEC(
                    provider=provider,
                    model=model,
                    agent=agent,
                    machine=machine,
                    api_spec=api_spec,
                    reasoning_effort=reasoning_effort,
                )
                cmd = _build_generic_agent_command(agent=agent, prompt_path=prompt_path, reasoning_effort=reasoning_effort)
            case "crush":
                assert provider is not None, "Provider must be specified for Crush agent."
                api_keys = get_api_keys(provider=provider)
                api_spec = api_keys[idx % len(api_keys)] if len(api_keys) > 0 else None
                if api_spec is None:
                    raise ValueError("No API keys found for Crush. Please configure them in dotfiles/creds/llm/crush/api_keys.ini")
                ai_spec = AI_SPEC(
                    provider=provider,
                    model=model,
                    agent=agent,
                    machine=machine,
                    api_spec=api_spec,
                    reasoning_effort=reasoning_effort,
                )
                from machineconfig.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_crush import fire_crush

                cmd = fire_crush(ai_spec=ai_spec, prompt_path=prompt_path, repo_root=repo_root)
            case "copilot":
                api_spec = API_SPEC(api_key=None, api_name="", api_label="", api_account="")
                ai_spec = AI_SPEC(
                    provider=provider,
                    model=model,
                    agent=agent,
                    machine=machine,
                    api_spec=api_spec,
                    reasoning_effort=reasoning_effort,
                )
                from machineconfig.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_copilot import fire_copilot

                cmd = fire_copilot(ai_spec=ai_spec, prompt_path=prompt_path, repo_root=repo_root)
            case "codex":
                api_keys = get_api_keys(provider="openai", silent_if_missing=True)
                api_spec = api_keys[idx % len(api_keys)] if len(api_keys) > 0 else API_SPEC(api_key=None, api_name="", api_label="", api_account="")
                ai_spec = AI_SPEC(
                    provider=provider,
                    model=model,
                    agent=agent,
                    machine=machine,
                    api_spec=api_spec,
                    reasoning_effort=reasoning_effort,
                )
                from machineconfig.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_codex import fire_codex

                cmd = fire_codex(ai_spec=ai_spec, prompt_path=prompt_path, repo_root=repo_root)
            case _:
                api_spec = API_SPEC(api_key=None, api_name="", api_label="", api_account="")
                ai_spec = AI_SPEC(
                    provider=provider,
                    model=model,
                    agent=agent,
                    machine=machine,
                    api_spec=api_spec,
                    reasoning_effort=reasoning_effort,
                )
                cmd = _build_generic_agent_command(agent=agent, prompt_path=prompt_path, reasoning_effort=reasoning_effort)
        cmd_prefix += f"""
echo "Running with api label:   {ai_spec["api_spec"]["api_label"]}"
echo "Running with api acount:  {ai_spec["api_spec"]["api_account"]}"
echo "Running with api name:    {ai_spec["api_spec"]["api_name"]}"
echo "Running with api key:     {ai_spec["api_spec"]["api_key"]}"
"""
        cmd_postfix = """
sleep 0.1
echo "---------END OF AGENT OUTPUT---------"
"""
        agent_cmd_launch_path.write_text(cmd_prefix + cmd + cmd_postfix, encoding="utf-8")


def get_agents_launch_layout(session_root: Path, *, job_name: str, start_dir: Path) -> LayoutsFile:
    prompt_directories = get_prompt_directories(prompt_root=session_root / "prompts")
    tab_config: list[TabConfig] = []
    for a_prompt_dir in prompt_directories:
        idx = a_prompt_dir.name.split("_")[-1]  # e.g., agent_0 -> 0
        agent_cmd_path = a_prompt_dir / AGENT_NAME_FORMATTER.format(idx=idx)
        fire_cmd = f"bash {shlex.quote(str(agent_cmd_path))}"
        tab_config.append(TabConfig(tabName=f"Agent{idx}", startDir=str(start_dir.resolve()), command=fire_cmd))
    layout = LayoutConfig(layoutName=job_name, layoutTabs=tab_config)
    layouts_file: LayoutsFile = LayoutsFile(version="1.0", layouts=[layout])
    return layouts_file


def get_prompt_directories(*, prompt_root: Path) -> list[Path]:
    import re

    prompt_directories = [path for path in prompt_root.iterdir() if path.is_dir()]
    return sorted(
        prompt_directories,
        key=lambda path: [int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", path.name)],
    )
