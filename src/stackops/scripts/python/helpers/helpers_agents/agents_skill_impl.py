from pathlib import Path


def add_skill(*, skill_name: str, directory: str | None) -> str | None:
    opensource_skills = {"agent-browser": "bunx skills add vercel-labs/agent-browser"}
    if directory is not None:
        agent_dir = Path(directory).expanduser().resolve()
        if not agent_dir.is_dir():
            raise ValueError(f"Provided directory '{directory}' does not exist or is not a directory.")
    else:
        agent_dir = Path.cwd()

    if skill_name not in opensource_skills:
        return f"Skill '{skill_name}' is not recognized. Please provide a valid skill name."

    from stackops.utils.code import exit_then_run_shell_script

    command = opensource_skills[skill_name]
    exit_then_run_shell_script(
        script=f"""
cd {agent_dir}
{command}
""",
        strict=False,
    )
    return None
