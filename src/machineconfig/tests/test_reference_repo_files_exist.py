from pathlib import Path


type UsedBy = tuple[str, ...]
type ReferenceUsersByPath = dict[str, UsedBy]


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if parent.joinpath("pyproject.toml").is_file())

# Hardcoded from .ai/references/*.txt. The tuple values keep the Python users inline.
REFERENCE_USERS_BY_PATH: ReferenceUsersByPath = {
    "pyproject.toml": (
        "src/machineconfig/scripts/python/ai/scripts/lint_and_type_check.py",
        "src/machineconfig/scripts/python/ai/scripts/lint_and_type_check_models.py",
        "src/machineconfig/utils/installer_utils/installer_runner.py",
        "src/machineconfig/utils/upgrade_packages.py",
        "tests/test_utils_upgrade_packages.py",
    ),
    "pyproject_init.sh": ("tests/test_utils_upgrade_packages.py",),
    "zensical.toml": (
        "src/machineconfig/scripts/python/helpers/helpers_devops/cli_self_docs.py",
        "tests/test_cli_self_docs.py",
    ),
    "jobs/shell/docker_build_and_publish.sh": (
        "src/machineconfig/scripts/python/helpers/helpers_devops/cli_self.py",
    ),
    "src/machineconfig/jobs/installer/installer_data.json": (
        "src/machineconfig/utils/installer_utils/installer_runner.py",
        "src/machineconfig/utils/installer_utils/installer_cli.py",
        "src/machineconfig/scripts/python/helpers/helpers_repos/download_repo_licenses.py",
    ),
    "src/machineconfig/jobs/installer/linux_scripts/nerdfont.sh": (
        "src/machineconfig/jobs/installer/python_scripts/nerdfont.py",
    ),
    "src/machineconfig/jobs/installer/powershell_scripts/install_fonts.ps1": (
        "src/machineconfig/jobs/installer/python_scripts/nerfont_windows_helper.py",
    ),
    "src/machineconfig/jobs/installer/linux_scripts/redis.sh": (
        "src/machineconfig/jobs/installer/python_scripts/redis.py",
    ),
    "src/machineconfig/jobs/installer/powershell_scripts/sysabc.ps1": (
        "src/machineconfig/jobs/installer/python_scripts/sysabc.py",
    ),
    "src/machineconfig/jobs/installer/linux_scripts/sysabc_ubuntu.sh": (
        "src/machineconfig/jobs/installer/python_scripts/sysabc.py",
    ),
    "src/machineconfig/jobs/installer/linux_scripts/sysabc_macos.sh": (
        "src/machineconfig/jobs/installer/python_scripts/sysabc.py",
    ),
    "src/machineconfig/jobs/installer/linux_scripts/wezterm.sh": (
        "src/machineconfig/jobs/installer/python_scripts/wezterm.py",
    ),
    "src/machineconfig/profile/mapper_data.yaml": (
        "src/machineconfig/scripts/python/helpers/helpers_devops/backup_config.py",
        "src/machineconfig/scripts/python/helpers/helpers_devops/cli_backup_retrieve.py",
        "src/machineconfig/scripts/python/helpers/helpers_devops/cli_data.py",
        "src/machineconfig/scripts/python/helpers/helpers_devops/devops_status_checks.py",
    ),
    "src/machineconfig/profile/mapper_dotfiles.yaml": (
        "src/machineconfig/profile/create_links.py",
        "src/machineconfig/profile/dotfiles_mapper.py",
        "src/machineconfig/scripts/python/helpers/helpers_devops/cli_config_dotfile.py",
        "src/machineconfig/scripts/python/helpers/helpers_devops/devops_status_checks.py",
    ),
    "src/machineconfig/scripts/nu/wrap_mcfg.nu": ("src/machineconfig/profile/create_helper.py",),
    "src/machineconfig/scripts/python/ai/scripts/lint_and_type_check.sh": (
        "src/machineconfig/scripts/python/ai/utils/generic.py",
        "src/machineconfig/scripts/python/ai/initai.py",
    ),
    "src/machineconfig/scripts/python/ai/scripts/lint_and_type_check.ps1": (
        "src/machineconfig/scripts/python/ai/utils/generic.py",
        "src/machineconfig/scripts/python/ai/initai.py",
    ),
    "src/machineconfig/scripts/python/ai/solutions/copilot/instructions/python/dev.instructions.md": (
        "src/machineconfig/scripts/python/ai/utils/shared.py",
        "src/machineconfig/scripts/python/ai/solutions/auggie/auggie.py",
        "src/machineconfig/scripts/python/ai/solutions/claude/claude.py",
        "src/machineconfig/scripts/python/ai/solutions/cline/cline.py",
        "src/machineconfig/scripts/python/ai/solutions/codex/codex.py",
        "src/machineconfig/scripts/python/ai/solutions/copilot/github_copilot.py",
        "src/machineconfig/scripts/python/ai/solutions/crush/crush.py",
        "src/machineconfig/scripts/python/ai/solutions/cursor/cursors.py",
        "src/machineconfig/scripts/python/ai/solutions/droid/droid.py",
        "src/machineconfig/scripts/python/ai/solutions/gemini/gemini.py",
        "src/machineconfig/scripts/python/ai/solutions/kilocode/kilocode.py",
        "src/machineconfig/scripts/python/ai/solutions/opencode/opencode.py",
        "src/machineconfig/scripts/python/ai/solutions/q/amazon_q.py",
        "src/machineconfig/scripts/python/ai/solutions/qwen_code/qwen_code.py",
        "src/machineconfig/scripts/python/ai/solutions/warp/warp.py",
        "src/machineconfig/scripts/python/ai/initai.py",
    ),
    "src/machineconfig/scripts/python/ai/solutions/copilot/privacy.md": (
        "src/machineconfig/scripts/python/ai/solutions/copilot/github_copilot.py",
    ),
    "src/machineconfig/scripts/python/ai/solutions/codex/config.toml": (
        "src/machineconfig/scripts/python/ai/solutions/codex/codex.py",
    ),
    "src/machineconfig/scripts/python/ai/solutions/gemini/instructions.md": (
        "src/machineconfig/scripts/python/ai/solutions/gemini/gemini.py",
    ),
    "src/machineconfig/scripts/python/ai/solutions/gemini/settings.json": (
        "src/machineconfig/scripts/python/ai/solutions/gemini/gemini.py",
    ),
    "src/machineconfig/scripts/python/ai/solutions/kilocode/privacy.md": (
        "src/machineconfig/scripts/python/ai/solutions/kilocode/kilocode.py",
    ),
    "src/machineconfig/scripts/python/ai/solutions/opencode/opencode.jsonc": (
        "src/machineconfig/scripts/python/ai/solutions/opencode/opencode.py",
    ),
    "src/machineconfig/scripts/python/helpers/helpers_agents/privacy/configs/aichat/config.yaml": (
        "src/machineconfig/scripts/python/helpers/helpers_agents/privacy/configs/common/privacy_orchestrator.py",
    ),
    "src/machineconfig/scripts/python/helpers/helpers_agents/privacy/configs/aider/.aider.conf.yml": (
        "src/machineconfig/scripts/python/helpers/helpers_agents/privacy/configs/common/privacy_orchestrator.py",
    ),
    "src/machineconfig/scripts/python/helpers/helpers_agents/privacy/configs/copilot/config.yml": (
        "src/machineconfig/scripts/python/helpers/helpers_agents/privacy/configs/common/privacy_orchestrator.py",
    ),
    "src/machineconfig/scripts/python/helpers/helpers_agents/privacy/configs/crush/crush.json": (
        "src/machineconfig/scripts/python/helpers/helpers_agents/privacy/configs/common/privacy_orchestrator.py",
    ),
    "src/machineconfig/scripts/python/helpers/helpers_agents/privacy/configs/gemini/settings.json": (
        "src/machineconfig/scripts/python/helpers/helpers_agents/privacy/configs/common/privacy_orchestrator.py",
    ),
    "src/machineconfig/scripts/python/helpers/helpers_devops/themes/choose_pwsh_theme.ps1": (
        "src/machineconfig/scripts/python/helpers/helpers_devops/cli_config_terminal.py",
    ),
    "src/machineconfig/scripts/python/helpers/helpers_devops/themes/choose_starship_theme.ps1": (
        "src/machineconfig/scripts/python/helpers/helpers_devops/cli_config_terminal.py",
    ),
    "src/machineconfig/scripts/python/helpers/helpers_devops/themes/choose_starship_theme.sh": (
        "src/machineconfig/scripts/python/helpers/helpers_devops/cli_config_terminal.py",
    ),
    "src/machineconfig/scripts/python/helpers/helpers_devops/themes/choose_windows_terminal_theme.ps1": (
        "src/machineconfig/scripts/python/helpers/helpers_devops/cli_config_terminal.py",
    ),
    "src/machineconfig/scripts/python/helpers/helpers_peek/scripts_linux/fzfg": (
        "src/machineconfig/scripts/python/helpers/helpers_peek/peek_impl.py",
    ),
    "src/machineconfig/scripts/python/helpers/helpers_peek/scripts_windows/fzfg.ps1": (
        "src/machineconfig/scripts/python/helpers/helpers_peek/peek_impl.py",
    ),
    "src/machineconfig/scripts/python/helpers/helpers_peek/scripts_macos/fzfg": (
        "src/machineconfig/scripts/python/helpers/helpers_peek/peek_impl.py",
    ),
    "src/machineconfig/settings/linters/.flake8": (
        "src/machineconfig/scripts/python/helpers/helpers_devops/cli_repos.py",
    ),
    "src/machineconfig/settings/linters/.mypy.ini": (
        "src/machineconfig/scripts/python/helpers/helpers_devops/cli_repos.py",
    ),
    "src/machineconfig/settings/linters/.pylintrc": (
        "src/machineconfig/scripts/python/helpers/helpers_devops/cli_repos.py",
    ),
    "src/machineconfig/settings/linters/.ruff.toml": (
        "src/machineconfig/scripts/python/helpers/helpers_devops/cli_repos.py",
    ),
    "src/machineconfig/settings/linters/ty.toml": (
        "src/machineconfig/scripts/python/helpers/helpers_devops/cli_repos.py",
    ),
    "src/machineconfig/settings/shells/bash/init.sh": (
        "src/machineconfig/profile/create_shell_profile.py",
        "src/machineconfig/scripts/python/helpers/helpers_devops/cli_self.py",
        "src/machineconfig/scripts/python/helpers/helpers_devops/devops_status_checks.py",
    ),
    "src/machineconfig/settings/shells/nushell/config.nu": (
        "src/machineconfig/profile/create_shell_profile.py",
    ),
    "src/machineconfig/settings/shells/nushell/env.nu": (
        "src/machineconfig/profile/create_shell_profile.py",
    ),
    "src/machineconfig/settings/shells/nushell/init.nu": (
        "src/machineconfig/profile/create_shell_profile.py",
    ),
    "src/machineconfig/settings/shells/pwsh/init.ps1": (
        "src/machineconfig/profile/create_shell_profile.py",
        "src/machineconfig/scripts/python/helpers/helpers_devops/devops_status_checks.py",
    ),
    "src/machineconfig/settings/shells/zsh/init.sh": (
        "src/machineconfig/profile/create_shell_profile.py",
        "src/machineconfig/scripts/python/helpers/helpers_devops/cli_self.py",
    ),
    "src/machineconfig/settings/zellij/layouts/st2.kdl": (
        "src/machineconfig/scripts/python/helpers/helpers_sessions/attach_impl.py",
    ),
    "src/machineconfig/setup_linux/web_shortcuts/interactive.sh": (
        "src/machineconfig/scripts/python/helpers/helpers_devops/cli_self.py",
    ),
    "src/machineconfig/setup_linux/web_shortcuts/live_from_github.sh": (
        "src/machineconfig/scripts/python/helpers/helpers_devops/cli_self.py",
    ),
    "src/machineconfig/setup_windows/web_shortcuts/interactive.ps1": (
        "src/machineconfig/scripts/python/helpers/helpers_devops/cli_self.py",
    ),
    "src/machineconfig/setup_windows/web_shortcuts/live_from_github.ps1": (
        "src/machineconfig/scripts/python/helpers/helpers_devops/cli_self.py",
    ),
    "src/machineconfig/utils/files/art/fat_croco.txt": (
        "src/machineconfig/utils/files/headers.py",
    ),
    "src/machineconfig/utils/files/art/halfwit_croco.txt": (
        "src/machineconfig/utils/files/headers.py",
    ),
    "src/machineconfig/utils/files/art/happy_croco.txt": (
        "src/machineconfig/utils/files/headers.py",
    ),
    "src/machineconfig/utils/files/art/water_croco.txt": (
        "src/machineconfig/utils/files/headers.py",
    ),
}


def test_reference_repo_files_exist() -> None:
    missing_entries: list[str] = []

    for relative_path, used_by in REFERENCE_USERS_BY_PATH.items():
        file_path = REPO_ROOT.joinpath(relative_path)
        if file_path.is_file():
            continue
        sources = "\n".join(f"  - {source}" for source in used_by)
        missing_entries.append(f"{relative_path}\n{sources}")
    assert not missing_entries, "Missing referenced repo files:\n\n" + "\n\n".join(missing_entries)
    print("All referenced repo files exist.")

if __name__ == "__main__":
    test_reference_repo_files_exist()
