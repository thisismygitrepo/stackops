from machineconfig.utils.path_extended import PathExtended, PLike
from machineconfig.utils.path_compression import delete_path
from pathlib import Path
from machineconfig.profile.create_links_export import ON_CONFLICT_STRICT
from machineconfig.utils.accessories import randstr
from rich.console import Console
from rich.panel import Panel
import hashlib
from typing import TypedDict, Literal

console = Console()


ActionType = Literal[
    "already_linked",
    "relinking",
    "fixing_broken_link",
    "identical_files",
    "backupConfigDefaultPath",
    "backing_up_source",
    "backing_up_target",
    "relink2newSelfManagedPath",
    "relinking_to_new_target",
    "move2selfManagedPath",
    "moving_to_target",
    "new_link",
    "newLinkAndSelfManagedPath",
    "new_link_and_target",
    "linking",
    "copying",
    "error"
]


class OperationResult(TypedDict):
    action: ActionType
    details: str

class OperationRecord(TypedDict):
    action: ActionType
    details: str
    program: str
    file_key: str
    defaultPath: str
    selfManaged: str
    operation: str
    status: str


def files_are_identical(file1: PathExtended, file2: PathExtended) -> bool:
    """Check if two files are identical by comparing their SHA256 hashes."""
    def get_file_hash(path: PathExtended) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    try:
        return get_file_hash(file1) == get_file_hash(file2)
    except (OSError, IOError):
        return False


def build_links(target_paths: list[tuple[PLike, str]], repo_root: PLike):
    """Build symboic links from various relevant paths (e.g. data) to `repo_root/links/<name>` to facilitate easy access from
    tree explorer of the IDE.
    """
    target_dirs_filtered: list[tuple[PathExtended, str]] = []
    for a_dir, a_name in target_paths:
        a_dir_obj = PathExtended(a_dir).resolve()
        if not a_dir_obj.exists():
            a_dir_obj.mkdir(parents=True, exist_ok=True)
        target_dirs_filtered.append((a_dir_obj, a_name))

    import git

    repo = git.Repo(repo_root, search_parent_directories=True)
    root_maybe = repo.working_tree_dir
    assert root_maybe is not None
    repo_root_obj = PathExtended(root_maybe)
    tmp_results_root = PathExtended.home().joinpath("tmp_results", "tmp_data", repo_root_obj.name)
    tmp_results_root.mkdir(parents=True, exist_ok=True)
    target_dirs_filtered.append((tmp_results_root, "tmp_results"))

    links_dir = repo_root_obj.joinpath("links")
    links_dir.mkdir(parents=True, exist_ok=True)
    
    for a_target_path, a_name in target_dirs_filtered:
        links_path = links_dir.joinpath(a_name)
        if links_path.exists() or links_path.is_symlink():
            if links_path.is_symlink() and links_path.resolve() == a_target_path.resolve():
                continue
            links_path.unlink(missing_ok=True)
        try:
            links_path.symlink_to(target=a_target_path)
        except OSError as ex:
            console.print(Panel(f"❌ Failed to create symlink {links_path} -> {a_target_path}: {ex}", title="Symlink Error", expand=False))


def symlink_map(config_file_default_path: Path, config_file_self_managed_path: Path,
                 on_conflict: ON_CONFLICT_STRICT
                 ) -> OperationResult:
    """helper function. creates a symlink from `config_file_default_path` to `config_file_self_managed_path`.

    Returns a dict with 'action' and 'details' keys describing what was done.

    on_conflict strategies:
    - throw-error: Raise exception when files differ
    - overwrite-self-managed: Delete config_file_self_managed_path (self-managed), move config_file_default_path to config_file_self_managed_path, create symlink
    - backup-self-managed: Backup config_file_self_managed_path (self-managed), move config_file_default_path to config_file_self_managed_path, create symlink
    - overwrite-default-path: Delete config_file_default_path (default path), create symlink to config_file_self_managed_path
    - backup-default-path: Backup config_file_default_path (default path), create symlink to config_file_self_managed_path

    Note: `config_file_default_path` is the default system location, `config_file_self_managed_path` is the self-managed config location

    """
    config_file_default_path = PathExtended(config_file_default_path).expanduser().absolute()
    config_file_self_managed_path = PathExtended(config_file_self_managed_path).expanduser().absolute()
    
    if config_file_default_path.resolve() == config_file_self_managed_path.resolve():
        raise ValueError(f"config_file_default_path and config_file_self_managed_path resolve to the same location: {config_file_default_path.resolve()}")
    
    action_taken: ActionType = "linking"
    details = "Creating symlink"
    
    # Handle broken symlinks first - they exist as symlinks but point to non-existent targets
    if config_file_default_path.is_symlink() and not config_file_default_path.exists():
        action_taken = "fixing_broken_link"
        details = "Removed broken symlink and will create new one"
        console.print(Panel(f"🔄 FIXING BROKEN LINK | Removing broken symlink {config_file_default_path}, will create link to {config_file_self_managed_path}", title="Fixing Broken Link", expand=False))
        config_file_default_path.unlink()
    
    # Case analysis based on docstring
    if config_file_default_path.exists():
        if config_file_self_managed_path.exists():
            if config_file_default_path.is_symlink():
                # Check if symlink already points to correct target
                try:
                    if config_file_default_path.resolve() == config_file_self_managed_path.resolve():
                        # Case: config_file_default_path exists AND config_file_self_managed_path exists AND config_file_default_path is a symlink pointing to config_file_self_managed_path
                        action_taken = "already_linked"
                        details = "Symlink already correctly points to target"
                        console.print(Panel(f"✅ ALREADY LINKED | {config_file_default_path} ➡️  {config_file_self_managed_path}", title="Already Linked", expand=False))
                        return {"action": action_taken, "details": details}
                    else:
                        # Case: config_file_default_path exists AND config_file_self_managed_path exists AND config_file_default_path is a symlink pointing to somewhere else
                        action_taken = "relinking"
                        details = "Updated existing symlink to point to new target"
                        console.print(Panel(f"🔄 RELINKING | Updating symlink from {config_file_default_path} ➡️  {config_file_self_managed_path}", title="Relinking", expand=False))
                        delete_path(config_file_default_path, verbose=True)
                except OSError:
                    # Broken symlink case
                    action_taken = "fixing_broken_link"
                    details = "Removed broken symlink and will create new one"
                    console.print(Panel(f"🔄 FIXING BROKEN LINK | Fixing broken symlink from {config_file_default_path} ➡️  {config_file_self_managed_path}", title="Fixing Broken Link", expand=False))
                    delete_path(config_file_default_path, verbose=True)
            else:
                # Case: config_file_default_path exists AND config_file_self_managed_path exists AND config_file_default_path is a concrete path
                if files_are_identical(config_file_default_path, config_file_self_managed_path):
                    # Files are identical, just delete this and create symlink
                    action_taken = "identical_files"
                    details = "Files identical, removed config_file_default_path and will create symlink"
                    console.print(Panel(f"🔗 IDENTICAL FILES | Files are identical, deleting {config_file_default_path} and creating symlink to {config_file_self_managed_path}", title="Identical Files", expand=False))
                    delete_path(config_file_default_path, verbose=True)
                else:
                    # Files are different, use on_conflict strategy
                    import subprocess
                    command = f"""delta  --paging never --side-by-side "{config_file_default_path}" "{config_file_self_managed_path}" """
                    try:
                        console.print(Panel(f"🆘 CONFLICT DETECTED | Showing diff between {config_file_default_path} and {config_file_self_managed_path}", title="Conflict Detected", expand=False))
                        subprocess.run(command, shell=True, check=True)
                    except Exception:
                        console.print(Panel("⚠️ Could not show diff using 'delta'. Please install 'delta' for better diff visualization.", title="Delta Not Found", expand=False))

                    match on_conflict:
                        case "throw-error":
                            raise RuntimeError(f"Conflict detected: {config_file_default_path} and {config_file_self_managed_path} both exist with different content")
                        case "overwrite-self-managed":
                            action_taken = "backing_up_target"
                            details = "Overwriting self-managed config, moving default path to self-managed location"
                            console.print(Panel(f"📦 OVERWRITE SELF-MANAGED | Deleting {config_file_self_managed_path}, moving {config_file_default_path} to {config_file_self_managed_path}", title="Overwrite Self-Managed", expand=False))
                            delete_path(config_file_self_managed_path, verbose=True)
                            config_file_default_path.move(path=config_file_self_managed_path)
                        case "backup-self-managed":
                            backup_name = f"{config_file_self_managed_path}.orig_{randstr()}"
                            action_taken = "backing_up_target"
                            details = f"Backed up self-managed config to {backup_name}"
                            console.print(Panel(f"📦 BACKUP SELF-MANAGED | Moving {config_file_self_managed_path} to {backup_name}, moving {config_file_default_path} to {config_file_self_managed_path}", title="Backup Self-Managed", expand=False))
                            config_file_self_managed_path.move(path=backup_name)
                            config_file_default_path.move(path=config_file_self_managed_path)
                        case "overwrite-default-path":
                            action_taken = "backupConfigDefaultPath"
                            details = "Overwriting default path, creating symlink to self-managed config"
                            console.print(Panel(f"📦 OVERWRITE DEFAULT | Deleting {config_file_default_path}, creating symlink to {config_file_self_managed_path}", title="Overwrite Default", expand=False))
                            delete_path(config_file_default_path, verbose=True)
                        case "backup-default-path":
                            backup_name = f"{config_file_default_path}.orig_{randstr()}"
                            action_taken = "backupConfigDefaultPath"
                            details = f"Backed up default path to {backup_name}"
                            console.print(Panel(f"📦 BACKUP DEFAULT | Moving {config_file_default_path} to {backup_name}, creating symlink to {config_file_self_managed_path}", title="Backup Default", expand=False))
                            config_file_default_path.move(path=backup_name)
        else:
            # config_file_self_managed_path doesn't exist
            if config_file_default_path.is_symlink():
                # Case: config_file_default_path exists AND config_file_self_managed_path doesn't exist AND config_file_default_path is a symlink (pointing anywhere)
                action_taken = "relink2newSelfManagedPath"
                details = "Removed existing symlink, will create config_file_self_managed_path and new symlink"
                console.print(Panel(f"🔄 RELINKING | Updating symlink from {config_file_default_path} ➡️  {config_file_self_managed_path}", title="Relinking", expand=False))
                delete_path(config_file_default_path, verbose=True)
                # Create config_file_self_managed_path
                config_file_self_managed_path.parent.mkdir(parents=True, exist_ok=True)
                config_file_self_managed_path.touch()
            else:
                # Case: config_file_default_path exists AND config_file_self_managed_path doesn't exist AND config_file_default_path is a concrete path
                action_taken = "move2selfManagedPath"
                details = "Moved config_file_default_path to config_file_self_managed_path location, will create symlink"
                console.print(Panel(f"📁 MOVING | Moving {config_file_default_path} to {config_file_self_managed_path}, then creating symlink", title="Moving", expand=False))
                config_file_default_path.move(path=config_file_self_managed_path)
    else:
        # config_file_default_path doesn't exist
        if config_file_self_managed_path.exists():
            # Case: config_file_default_path doesn't exist AND config_file_self_managed_path exists
            action_taken = "new_link"
            details = "Creating new symlink to existing config_file_self_managed_path"
            console.print(Panel(f"🆕 NEW LINK | Creating new symlink from {config_file_default_path} ➡️  {config_file_self_managed_path}", title="New Link", expand=False))
        else:
            # Case: config_file_default_path doesn't exist AND config_file_self_managed_path doesn't exist
            action_taken = "newLinkAndSelfManagedPath"
            details = "Creating config_file_self_managed_path file and new symlink"
            console.print(Panel(f"🆕 NEW LINK & TARGET | Creating {config_file_self_managed_path} and symlink from {config_file_default_path} ➡️  {config_file_self_managed_path}", title="New Link & Target", expand=False))
            config_file_self_managed_path.parent.mkdir(parents=True, exist_ok=True)
            config_file_self_managed_path.touch()
    
    # Create the symlink
    try:
        PathExtended(config_file_default_path).symlink_to(target=config_file_self_managed_path, verbose=True, overwrite=False)
        return {"action": action_taken, "details": details}
    except Exception as ex:
        action_taken = "error"
        details = f"Failed to create symlink: {str(ex)}"
        console.print(Panel(f"❌ ERROR | Failed at linking {config_file_default_path} ➡️  {config_file_self_managed_path}. Reason: {ex}", title="Error", expand=False))
        return {"action": action_taken, "details": details}


def copy_map(config_file_default_path: PathExtended, config_file_self_managed_path: PathExtended, on_conflict: ON_CONFLICT_STRICT) -> OperationResult:
    config_file_default_path = PathExtended(config_file_default_path).expanduser().absolute()
    config_file_self_managed_path = PathExtended(config_file_self_managed_path).expanduser().absolute()
    
    if config_file_default_path.resolve() == config_file_self_managed_path.resolve():
        raise ValueError(f"config_file_default_path and config_file_self_managed_path resolve to the same location: {config_file_default_path.resolve()}")
    
    action_taken: ActionType = "copying"
    details = "Copying file"
    
    # Handle broken symlinks first - they exist as symlinks but point to non-existent targets
    if config_file_default_path.is_symlink() and not config_file_default_path.exists():
        action_taken = "fixing_broken_link"
        details = "Removed broken symlink and will copy new file"
        console.print(Panel(f"🔄 FIXING BROKEN LINK | Removing broken symlink {config_file_default_path}, will copy from {config_file_self_managed_path}", title="Fixing Broken Link", expand=False))
        config_file_default_path.unlink()
    
    match (config_file_default_path.exists(), config_file_self_managed_path.exists()):
        case (True, True):
            # Both files exist
            if config_file_default_path.is_symlink():
                try:
                    if config_file_default_path.resolve() == config_file_self_managed_path.resolve():
                        action_taken = "already_linked"
                        details = "File at default path is already a symlink to self-managed config"
                        console.print(Panel(f"✅ ALREADY CORRECT | {config_file_default_path} already points to {config_file_self_managed_path}", title="Already Correct", expand=False))
                        return {"action": action_taken, "details": details}
                    else:
                        action_taken = "relinking"
                        details = "Removing symlink at default path that points elsewhere"
                        console.print(Panel(f"🔄 REMOVING SYMLINK | Removing symlink {config_file_default_path} (points elsewhere), will copy from {config_file_self_managed_path}", title="Removing Symlink", expand=False))
                        delete_path(config_file_default_path, verbose=True)
                except OSError:
                    action_taken = "fixing_broken_link"
                    details = "Removed broken symlink at default path"
                    console.print(Panel(f"🔄 FIXING BROKEN SYMLINK | Removing broken symlink {config_file_default_path}, will copy from {config_file_self_managed_path}", title="Fixing Broken Symlink", expand=False))
                    delete_path(config_file_default_path, verbose=True)
            else:
                # Check if files are identical first
                if files_are_identical(config_file_default_path, config_file_self_managed_path):
                    # Files are identical, just delete this and proceed with copy
                    action_taken = "identical_files"
                    details = "Files identical, removed config_file_default_path and will copy"
                    console.print(Panel(f"🔗 IDENTICAL FILES | Files are identical, deleting {config_file_default_path} and copying from {config_file_self_managed_path}", title="Identical Files", expand=False))
                    delete_path(config_file_default_path, verbose=True)
                else:
                    # Files are different, use on_conflict strategy
                    import subprocess
                    command = f"""delta  --paging never --side-by-side "{config_file_default_path}" "{config_file_self_managed_path}" """
                    try:
                        console.print(Panel(f"🆘 CONFLICT DETECTED | Showing diff between {config_file_default_path} and {config_file_self_managed_path}", title="Conflict Detected", expand=False))
                        subprocess.run(command, shell=True, check=True)
                    except Exception:
                        console.print(Panel("⚠️ Could not show diff using 'delta'. Please install 'delta' for better diff visualization.", title="Delta Not Found", expand=False))

                    match on_conflict:
                        case "throw-error":
                            raise RuntimeError(f"Conflict detected: {config_file_default_path} and {config_file_self_managed_path} both exist with different content")
                        case "overwrite-self-managed":
                            action_taken = "backing_up_target"
                            details = "Overwriting self-managed config with default path content"
                            console.print(Panel(f"📦 OVERWRITE SELF-MANAGED | Deleting {config_file_self_managed_path}, moving {config_file_default_path} to {config_file_self_managed_path}", title="Overwrite Self-Managed", expand=False))
                            delete_path(config_file_self_managed_path, verbose=True)
                            config_file_default_path.move(path=config_file_self_managed_path)
                        case "backup-self-managed":
                            backup_name = f"{config_file_self_managed_path}.orig_{randstr()}"
                            action_taken = "backing_up_target"
                            details = f"Backed up self-managed config to {backup_name}"
                            console.print(Panel(f"📦 BACKUP SELF-MANAGED | Moving {config_file_self_managed_path} to {backup_name}, moving {config_file_default_path} to {config_file_self_managed_path}", title="Backup Self-Managed", expand=False))
                            config_file_self_managed_path.move(path=backup_name)
                            config_file_default_path.move(path=config_file_self_managed_path)
                        case "overwrite-default-path":
                            action_taken = "backupConfigDefaultPath"
                            details = "Overwriting default path with self-managed config"
                            console.print(Panel(f"📦 OVERWRITE DEFAULT | Deleting {config_file_default_path}, will copy from {config_file_self_managed_path}", title="Overwrite Default", expand=False))
                            delete_path(config_file_default_path, verbose=True)
                        case "backup-default-path":
                            backup_name = f"{config_file_default_path}.orig_{randstr()}"
                            action_taken = "backupConfigDefaultPath"
                            details = f"Backed up default path to {backup_name}"
                            console.print(Panel(f"📦 BACKUP DEFAULT | Moving {config_file_default_path} to {backup_name}, will copy from {config_file_self_managed_path}", title="Backup Default", expand=False))
                            config_file_default_path.move(path=backup_name)
        case (True, False):
            # config_file_default_path exists, config_file_self_managed_path doesn't
            if config_file_default_path.is_symlink():
                action_taken = "relink2newSelfManagedPath"
                details = "Removed existing symlink, will create config_file_self_managed_path and copy"
                console.print(Panel(f"🔄 REMOVING SYMLINK | Removing symlink {config_file_default_path}, creating {config_file_self_managed_path}", title="Removing Symlink", expand=False))
                delete_path(config_file_default_path, verbose=True)
                config_file_self_managed_path.parent.mkdir(parents=True, exist_ok=True)
                config_file_self_managed_path.touch()
            else:
                action_taken = "move2selfManagedPath"
                details = "Moved config_file_default_path to config_file_self_managed_path location, will copy back"
                console.print(Panel(f"📁 MOVING | Moving {config_file_default_path} to {config_file_self_managed_path}, then copying back", title="Moving", expand=False))
                config_file_default_path.move(path=config_file_self_managed_path)
        case (False, True):
            # config_file_default_path doesn't exist, config_file_self_managed_path does
            action_taken = "new_link"
            details = "Copying existing config_file_self_managed_path to config_file_default_path location"
            console.print(Panel(f"🆕 NEW COPY | Copying {config_file_self_managed_path} to {config_file_default_path}", title="New Copy", expand=False))
        case (False, False):
            # Neither exists
            action_taken = "newLinkAndSelfManagedPath"
            details = "Creating config_file_self_managed_path file and copying to config_file_default_path"
            console.print(Panel(f"🆕 NEW FILE & COPY | Creating {config_file_self_managed_path} and copying to {config_file_default_path}", title="New File & Copy", expand=False))
            config_file_self_managed_path.parent.mkdir(parents=True, exist_ok=True)
            config_file_self_managed_path.touch()
    
    try:
        config_file_self_managed_path.copy(path=config_file_default_path, overwrite=True, verbose=True)
        return {"action": action_taken, "details": details}
    except Exception as ex:
        action_taken = "error"
        details = f"Failed to copy file: {str(ex)}"
        console.print(Panel(f"❌ ERROR | Failed at copying {config_file_self_managed_path} to {config_file_default_path}. Reason: {ex}", title="Error", expand=False))
        return {"action": action_taken, "details": details}
