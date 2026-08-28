import random
from math import isfinite
from pathlib import Path

import stackops.scripts.python.helpers.helpers_agents.agents_shell as agent_shell
from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS, HOST, PROVIDER, AI_SPEC, API_SPEC, DEFAULT_STAGGER_MAX
from stackops.scripts.python.helpers.helpers_agents.reasoning_capabilities import ReasoningEffort
from stackops.utils.schemas.layouts.layout_types import LayoutConfig, LayoutsFile, TabConfig
from stackops.utils.source_of_truth import dotfiles_llm_api_keys_path


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


def _build_generic_agent_command(
    agent: AGENTS, prompt_path: Path, reasoning_effort: ReasoningEffort | None, model: str | None, provider: PROVIDER | None, *, is_windows: bool
) -> str:
    from stackops.scripts.python.helpers.helpers_agents.agents_run_impl import build_agent_command

    return build_agent_command(
        agent=agent, prompt_file=prompt_path, reasoning_effort=reasoning_effort, model=model, provider=provider, is_windows=is_windows
    )


def _without_api_key(*, ai_spec: AI_SPEC) -> AI_SPEC:
    api_spec = ai_spec["api_spec"]
    return AI_SPEC(
        provider=ai_spec["provider"],
        model=ai_spec["model"],
        agent=ai_spec["agent"],
        machine=ai_spec["machine"],
        api_spec=API_SPEC(
            api_key=None,
            api_name=api_spec["api_name"],
            api_label=api_spec["api_label"],
            api_account=api_spec["api_account"],
        ),
        reasoning_effort=ai_spec["reasoning_effort"],
    )


def _runtime_api_key_environment_lines(
    *, env_name: str, provider: PROVIDER, api_spec: API_SPEC, is_windows: bool
) -> list[str]:
    if api_spec["api_key"] is None:
        warning_message = f"Warning: No configured API key provided, hoping {env_name} is set in the environment."
        return [agent_shell.render_output(message=warning_message, is_windows=is_windows)]

    api_key_path = dotfiles_llm_api_keys_path(provider)
    api_label = api_spec["api_label"]
    resolver_code = (
        "import configparser\n"
        "import sys\n"
        "config = configparser.ConfigParser(interpolation=None)\n"
        f"config.read({str(api_key_path)!r}, encoding='utf-8')\n"
        f"api_key = config[{api_label!r}]['api_key'].strip()\n"
        "if not api_key:\n"
        "    raise RuntimeError('Configured API key is empty.')\n"
        "sys.stdout.write(api_key)\n"
    )
    resolver_command = agent_shell.build_shell_invocation(
        executable="uv",
        arguments=["run", "--no-project", "--quiet", "python", "-c", resolver_code],
        is_windows=is_windows,
    )
    if is_windows:
        return [
            f"$env:{env_name} = (& {resolver_command})",
            "if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }",
        ]
    return [
        f'{env_name}="$({resolver_command})" || exit $?',
        f"export {env_name}",
    ]


def _forward_docker_environment(*, command: str, env_name: str) -> str:
    marker = "docker run -it --rm \\\n"
    if marker not in command:
        raise RuntimeError("Docker agent command does not contain the expected docker run invocation.")
    replacement = f"docker run -it --rm \\\n  -e {env_name} \\\n"
    return command.replace(marker, replacement, 1)


def get_api_keys(provider: PROVIDER, *, silent_if_missing: bool = False) -> list[API_SPEC]:
    from stackops.utils.io import read_ini

    api_key_path = dotfiles_llm_api_keys_path(provider)
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
    stagger_max: float = DEFAULT_STAGGER_MAX,
) -> None:
    if not isfinite(stagger_max) or stagger_max < 0:
        raise ValueError("stagger_max must be a finite number greater than or equal to 0")

    if agent == "codex":
        if provider is None:
            provider = "openai"
        elif provider != "openai":
            raise ValueError("Codex agent only works with openai provider.")

    agents_dir.mkdir(parents=True, exist_ok=True)
    prompt_folder = agents_dir / "prompts"
    prompt_folder.mkdir(parents=True, exist_ok=True)
    is_windows = agent_shell.is_windows_host()

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
            prompt_path.write_text(prompt_prefix + f"""\nPlease only look at:\n{material_reference}.""" + JURISDICTION_SUFFIX, encoding="utf-8")

        agent_cmd_launch_path = prompt_root / agent_shell.get_agent_command_filename(idx=idx, is_windows=is_windows)
        random_sleep_time = random.uniform(0, stagger_max)
        ai_spec: AI_SPEC
        api_key_environment_name: str | None = None
        match agent:
            case "cursor-agent":
                api_spec = API_SPEC(api_key=None, api_name="", api_label="", api_account="")
                ai_spec = AI_SPEC(provider=provider, model=model, agent=agent, machine=machine, api_spec=api_spec, reasoning_effort=reasoning_effort)
                cmd = _build_generic_agent_command(
                    agent=agent,
                    prompt_path=prompt_path,
                    reasoning_effort=reasoning_effort,
                    model=ai_spec["model"],
                    provider=ai_spec["provider"],
                    is_windows=is_windows,
                )
            case "crush":
                assert provider is not None, "Provider must be specified for Crush agent."
                api_keys = get_api_keys(provider=provider)
                api_spec = api_keys[idx % len(api_keys)] if len(api_keys) > 0 else None
                if api_spec is None:
                    raise ValueError(f"No API keys found for Crush. Please configure them in {dotfiles_llm_api_keys_path(provider)}")
                ai_spec = AI_SPEC(provider=provider, model=model, agent=agent, machine=machine, api_spec=api_spec, reasoning_effort=reasoning_effort)
                if machine == "local":
                    cmd = _build_generic_agent_command(
                        agent=agent,
                        prompt_path=prompt_path,
                        reasoning_effort=reasoning_effort,
                        model=ai_spec["model"],
                        provider=ai_spec["provider"],
                        is_windows=is_windows,
                    )
                else:
                    from stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_crush import CRUSH_API_KEY_ENV, fire_crush

                    api_key_environment_name = CRUSH_API_KEY_ENV
                    cmd = fire_crush(ai_spec=_without_api_key(ai_spec=ai_spec), prompt_path=prompt_path, repo_root=repo_root)
            case "copilot":
                api_spec = API_SPEC(api_key=None, api_name="", api_label="", api_account="")
                ai_spec = AI_SPEC(provider=provider, model=model, agent=agent, machine=machine, api_spec=api_spec, reasoning_effort=reasoning_effort)
                if machine == "local":
                    cmd = _build_generic_agent_command(
                        agent=agent,
                        prompt_path=prompt_path,
                        reasoning_effort=reasoning_effort,
                        model=ai_spec["model"],
                        provider=ai_spec["provider"],
                        is_windows=is_windows,
                    )
                else:
                    from stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_copilot import fire_copilot

                    cmd = fire_copilot(ai_spec=ai_spec, prompt_path=prompt_path, repo_root=repo_root)
            case "codex":
                api_keys = get_api_keys(provider="openai", silent_if_missing=True)
                api_spec = api_keys[idx % len(api_keys)] if len(api_keys) > 0 else API_SPEC(api_key=None, api_name="", api_label="", api_account="")
                ai_spec = AI_SPEC(provider=provider, model=model, agent=agent, machine=machine, api_spec=api_spec, reasoning_effort=reasoning_effort)
                api_key_environment_name = "CODEX_API_KEY"
                if machine == "local":
                    cmd = _build_generic_agent_command(
                        agent=agent,
                        prompt_path=prompt_path,
                        reasoning_effort=reasoning_effort,
                        model=ai_spec["model"],
                        provider=ai_spec["provider"],
                        is_windows=is_windows,
                    )
                else:
                    from stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_codex import fire_codex

                    cmd = fire_codex(ai_spec=_without_api_key(ai_spec=ai_spec), prompt_path=prompt_path, repo_root=repo_root)
                    cmd = _forward_docker_environment(command=cmd, env_name=api_key_environment_name)
            case "pi":
                api_spec = API_SPEC(api_key=None, api_name="", api_label="", api_account="")
                ai_spec = AI_SPEC(provider=provider, model=model, agent=agent, machine=machine, api_spec=api_spec, reasoning_effort=reasoning_effort)
                if machine == "local":
                    cmd = _build_generic_agent_command(
                        agent=agent,
                        prompt_path=prompt_path,
                        reasoning_effort=reasoning_effort,
                        model=ai_spec["model"],
                        provider=ai_spec["provider"],
                        is_windows=is_windows,
                    )
                else:
                    from stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_pi import fire_pi

                    cmd = fire_pi(ai_spec=ai_spec, prompt_path=prompt_path, repo_root=repo_root)
            case _:
                api_spec = API_SPEC(api_key=None, api_name="", api_label="", api_account="")
                ai_spec = AI_SPEC(provider=provider, model=model, agent=agent, machine=machine, api_spec=api_spec, reasoning_effort=reasoning_effort)
                cmd = _build_generic_agent_command(
                    agent=agent,
                    prompt_path=prompt_path,
                    reasoning_effort=reasoning_effort,
                    model=ai_spec["model"],
                    provider=ai_spec["provider"],
                    is_windows=is_windows,
                )

        script_lines: list[str] = []
        if is_windows:
            script_lines.append("$ErrorActionPreference = 'Stop'")
        else:
            script_lines.append("#!/usr/bin/env bash")
        script_lines.append("")
        script_lines.append(
            agent_shell.render_output(
                message=f"Using machine: {machine}, model: {model}, reasoning_effort: {reasoning_effort}, provider: {provider}, and agent: {agent}",
                is_windows=is_windows,
            )
        )
        script_lines.append(agent_shell.render_output(message=f"{job_name}-{idx} CMD {agent_cmd_launch_path}", is_windows=is_windows))
        script_lines.append(agent_shell.render_output(message=f"{job_name}-{idx} PROMPT {prompt_path}", is_windows=is_windows))
        script_lines.append(agent_shell.render_output(message=f"{job_name}-{idx} CONTEXT {prompt_material_path}", is_windows=is_windows))
        script_lines.append("")
        script_lines.append(agent_shell.render_env_assignment(name="FIRE_AGENTS_AGENT_NAME", value=agent, is_windows=is_windows))
        script_lines.append(agent_shell.render_env_assignment(name="FIRE_AGENTS_JOB_NAME", value=job_name, is_windows=is_windows))
        script_lines.append(agent_shell.render_env_assignment(name="FIRE_AGENTS_PROMPT_FILE", value=str(prompt_path), is_windows=is_windows))
        script_lines.append(
            agent_shell.render_env_assignment(name="FIRE_AGENTS_MATERIAL_FILE", value=str(prompt_material_path), is_windows=is_windows)
        )
        script_lines.append(
            agent_shell.render_env_assignment(name="FIRE_AGENTS_AGENT_LAUNCHER", value=str(agent_cmd_launch_path), is_windows=is_windows)
        )
        if api_key_environment_name is not None:
            selected_provider = ai_spec["provider"]
            if selected_provider is None:
                raise RuntimeError(f"Provider is required to resolve the {api_key_environment_name} credential.")
            script_lines.extend(
                _runtime_api_key_environment_lines(
                    env_name=api_key_environment_name,
                    provider=selected_provider,
                    api_spec=ai_spec["api_spec"],
                    is_windows=is_windows,
                )
            )
        script_lines.append("")
        script_lines.append(
            agent_shell.render_output(
                message=f"Sleeping for {random_sleep_time:.2f} seconds to stagger agent startups ... Press Ctrl+C to cancel.", is_windows=is_windows
            )
        )
        script_lines.append(agent_shell.render_sleep_seconds(seconds=random_sleep_time, is_windows=is_windows))
        script_lines.append(agent_shell.render_output(message="--------START OF AGENT OUTPUT--------", is_windows=is_windows))
        script_lines.append(agent_shell.render_sleep_milliseconds(milliseconds=100, is_windows=is_windows))
        script_lines.append(cmd.strip())
        script_lines.append("")
        script_lines.append(agent_shell.render_output(message=f"Running with api label:   {ai_spec['api_spec']['api_label']}", is_windows=is_windows))
        script_lines.append(
            agent_shell.render_output(message=f"Running with api acount:  {ai_spec['api_spec']['api_account']}", is_windows=is_windows)
        )
        script_lines.append(agent_shell.render_output(message=f"Running with api name:    {ai_spec['api_spec']['api_name']}", is_windows=is_windows))
        script_lines.append(agent_shell.render_sleep_milliseconds(milliseconds=100, is_windows=is_windows))
        script_lines.append(agent_shell.render_output(message="---------END OF AGENT OUTPUT---------", is_windows=is_windows))
        script_lines.append("")
        agent_cmd_launch_path.write_text("\n".join(script_lines), encoding="utf-8")


def get_agents_launch_layout(session_root: Path, *, job_name: str, start_dir: Path) -> LayoutsFile:
    prompt_directories = get_prompt_directories(prompt_root=session_root / "prompts")
    tab_config: list[TabConfig] = []
    is_windows = agent_shell.is_windows_host()
    for a_prompt_dir in prompt_directories:
        idx = a_prompt_dir.name.split("_")[-1]  # e.g., agent_0 -> 0
        agent_cmd_path = a_prompt_dir / agent_shell.get_agent_command_filename(idx=idx, is_windows=is_windows)
        fire_cmd = agent_shell.get_script_runner_command(script_path=agent_cmd_path, is_windows=is_windows)
        tab_config.append(TabConfig(tabName=f"Agent{idx}", startDir=str(start_dir.resolve()), command=fire_cmd))
    layout = LayoutConfig(layoutName=job_name, layoutTabs=tab_config)
    layouts_file: LayoutsFile = LayoutsFile(version="1.0", layouts=[layout])
    return layouts_file


def get_prompt_directories(*, prompt_root: Path) -> list[Path]:
    import re

    prompt_directories = [path for path in prompt_root.iterdir() if path.is_dir()]
    return sorted(prompt_directories, key=lambda path: [int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", path.name)])
