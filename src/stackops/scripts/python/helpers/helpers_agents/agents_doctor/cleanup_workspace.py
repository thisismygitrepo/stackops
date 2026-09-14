from git.exc import InvalidGitRepositoryError, NoSuchPathError
from git.repo import Repo

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_paths import validate_cleanup_path
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.command import resolve_resource_focuses
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.models import HookDiagnostic, HookEntry, HookInventory, HookRemoval
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.paths import permitted_resource_path
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorContext, DoctorResourceFocus


def resolve_cleanup_resources(*, requested_resources: str) -> tuple[tuple[DoctorResourceFocus, ...], bool]:
    resources = tuple(resource.strip().casefold() for resource in requested_resources.split(","))
    if "all" in resources and len(resources) > 1:
        raise ValueError("Do not mix 'all' with specific resource focuses")
    agent_resources = tuple(resource for resource in resources if resource != "workspace")
    focuses = resolve_resource_focuses(requested_resources=",".join(agent_resources)) if agent_resources else ()
    return focuses, "workspace" in resources or "all" in resources


def collect_workspace_resources(*, context: DoctorContext, recursive: bool) -> HookInventory:
    root = context.working_directory
    entries: list[HookEntry] = []
    diagnostics: list[HookDiagnostic] = []
    pending = [root]
    while pending:
        repository = pending.pop()
        if not permitted_resource_path(path=repository, home_directory=context.home_directory):
            continue
        try:
            validate_cleanup_path(path=repository, home_directory=context.home_directory, allow_leaf_symlink=False)
            if not permitted_resource_path(path=repository / ".git", home_directory=context.home_directory):
                continue
            try:
                Repo(repository, search_parent_directories=False)
            except (InvalidGitRepositoryError, NoSuchPathError):
                if repository == root or recursive:
                    pending.extend(
                        child for child in sorted(repository.iterdir(), reverse=True)
                        if (not recursive or not child.name.startswith("."))
                        and permitted_resource_path(path=child, home_directory=context.home_directory)
                        and not child.is_symlink() and child.is_dir()
                    )
                continue
            workspace = repository / ".ai"
            validate_cleanup_path(path=workspace, home_directory=context.home_directory, allow_leaf_symlink=True)
            linked = workspace.is_symlink()
            if not linked and not workspace.is_dir():
                continue
            entries.append(HookEntry(
                agent="shared", origin="local", path=workspace, name=f"""{repository.name}/.ai""", event="workspace",
                command="Remove shared .ai workspace files", state="configured",
                removal=HookRemoval(path=workspace, format="file" if linked else "directory", selector=(), action="delete"),
            ))
        except (OSError, ValueError) as error:
            diagnostics.append(HookDiagnostic("shared", "local", repository, str(error), "error"))
    return HookInventory(entries=tuple(entries), diagnostics=tuple(diagnostics))
