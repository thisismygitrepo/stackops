import shutil
import tempfile
from pathlib import Path

from stackops.scripts.python.helpers.helpers_ai_account.constants import DOTFILES_LLM_CREDENTIALS_RELATIVE_PATH, PRIVATE_CREDENTIAL_FILE_MODE
from stackops.scripts.python.helpers.helpers_ai_account.models import AutoRefreshUnavailableError, FileAgentSupport, RuntimeContext


def expand_path(path: Path) -> Path:
    expanded_path = path.expanduser()
    return expanded_path.resolve()


def profile_root(support: FileAgentSupport, context: RuntimeContext) -> Path:
    credentials_root = context.home / DOTFILES_LLM_CREDENTIALS_RELATIVE_PATH
    return credentials_root / support.backup_directory_name


def list_profile_directories(source_root: Path) -> list[Path]:
    if not source_root.exists():
        raise FileNotFoundError(f"Source directory does not exist: {source_root}")
    if not source_root.is_dir():
        raise NotADirectoryError(f"Source path is not a directory: {source_root}")
    return sorted((path for path in source_root.iterdir() if path.is_dir()), key=lambda path: path.name.casefold())


def profile_credential(profile_directory: Path, support: FileAgentSupport) -> Path:
    credential_path = profile_directory / support.profile_file_name
    return credential_path


def select_named_profile(profile_directories: list[Path], profile_name: str) -> Path:
    profiles_by_name = {path.name: path for path in profile_directories}
    selected_profile = profiles_by_name.get(profile_name)
    if selected_profile is None:
        raise ValueError(f"Profile not found: {profile_name}")
    return selected_profile


def copy_private_credential(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(f"Credential file does not exist: {source}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary_file:
        temporary_path = Path(temporary_file.name)

    try:
        shutil.copy2(source, temporary_path)
        temporary_path.chmod(PRIVATE_CREDENTIAL_FILE_MODE)
        temporary_path.replace(destination)
        destination.chmod(PRIVATE_CREDENTIAL_FILE_MODE)
    finally:
        temporary_path.unlink(missing_ok=True)


def find_refresh_profile(
    support: FileAgentSupport,
    profile_directories: list[Path],
    active_credential: Path,
) -> Path:
    identity_reader = support.read_identity
    if identity_reader is None:
        raise AutoRefreshUnavailableError(f"{support.display_name} requires --profile with --refresh")

    active_identity = identity_reader(active_credential)
    if active_identity is None:
        raise AutoRefreshUnavailableError(
            f"The active {support.display_name} credential has no safe automatic profile identity; pass --profile"
        )

    matching_profiles: list[Path] = []
    for profile_directory in profile_directories:
        backup_credential = profile_credential(profile_directory=profile_directory, support=support)
        if not backup_credential.is_file():
            raise FileNotFoundError(f"Profile has no credential file: {backup_credential}")
        backup_identity = identity_reader(backup_credential)
        if backup_identity == active_identity:
            matching_profiles.append(profile_directory)

    if len(matching_profiles) == 0:
        raise ValueError(f"No {support.agent} backup profile matches the active credential")
    if len(matching_profiles) > 1:
        profile_names = ", ".join(profile.name for profile in matching_profiles)
        raise ValueError(f"Multiple {support.agent} backup profiles match the active credential: {profile_names}")
    return matching_profiles[0]
