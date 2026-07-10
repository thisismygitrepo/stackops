import hashlib
import json
import shutil
import tempfile
from pathlib import Path

from stackops.scripts.python.helpers.helpers_ai_account.constants import (
    AUTOMATIC_PROFILE_FINGERPRINT_LENGTH,
    AUTOMATIC_PROFILE_NAME_PREFIX,
    DOTFILES_LLM_CREDENTIALS_RELATIVE_PATH,
    PRIVATE_CREDENTIAL_FILE_MODE,
    TEMPORARY_PROFILE_NAME_PREFIX,
)
from stackops.scripts.python.helpers.helpers_ai_account.models import AutomaticProfileSelectionUnavailableError, FileAgentSupport, RuntimeContext


class ProfilePublicationConflictError(FileExistsError):
    pass


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
    return sorted(
        (
            path
            for path in source_root.iterdir()
            if path.is_dir() and not path.name.startswith(TEMPORARY_PROFILE_NAME_PREFIX)
        ),
        key=lambda path: path.name.casefold(),
    )


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


def create_private_credential_profile(
    source: Path,
    profile_directory: Path,
    support: FileAgentSupport,
) -> None:
    if profile_directory.exists():
        raise ProfilePublicationConflictError(f"Automatic profile destination already exists: {profile_directory}")

    profile_directory.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        dir=profile_directory.parent,
        prefix=TEMPORARY_PROFILE_NAME_PREFIX,
    ) as temporary_directory_name:
        temporary_directory = Path(temporary_directory_name)
        temporary_credential = profile_credential(profile_directory=temporary_directory, support=support)
        copy_private_credential(source=source, destination=temporary_credential)
        try:
            temporary_directory.replace(profile_directory)
        except OSError as error:
            if not profile_directory.exists():
                raise
            raise ProfilePublicationConflictError(f"Automatic profile destination was created concurrently: {profile_directory}") from error


def backup_private_credential_automatically(
    support: FileAgentSupport,
    profiles_root: Path,
    profile_directories: list[Path],
    active_credential: Path,
) -> Path:
    identity_reader = support.read_identity
    if identity_reader is None:
        raise AutomaticProfileSelectionUnavailableError(f"{support.display_name} requires --profile for backup")

    active_identity = identity_reader(active_credential)
    if active_identity is None:
        raise AutomaticProfileSelectionUnavailableError(
            f"The active {support.display_name} credential has no safe automatic profile identity; pass --profile for backup"
        )

    matching_profiles: list[Path] = []
    for profile_directory in profile_directories:
        backup_credential = profile_credential(profile_directory=profile_directory, support=support)
        if not backup_credential.is_file():
            raise FileNotFoundError(f"Profile has no credential file: {backup_credential}")
        backup_identity = identity_reader(backup_credential)
        if backup_identity == active_identity:
            matching_profiles.append(profile_directory)

    if len(matching_profiles) > 1:
        profile_names = ", ".join(profile.name for profile in matching_profiles)
        raise ValueError(f"Multiple {support.agent} backup profiles match the active credential: {profile_names}")
    if len(matching_profiles) == 1:
        matching_profile = matching_profiles[0]
        matching_credential = profile_credential(profile_directory=matching_profile, support=support)
        copy_private_credential(source=active_credential, destination=matching_credential)
        return matching_profile

    serialized_identity = json.dumps(active_identity, ensure_ascii=True, separators=(",", ":"))
    identity_fingerprint = hashlib.sha256(serialized_identity.encode("utf-8")).hexdigest()[:AUTOMATIC_PROFILE_FINGERPRINT_LENGTH]
    automatic_profile_name = f"{AUTOMATIC_PROFILE_NAME_PREFIX}-{identity_fingerprint}"
    collision_index = 1
    while True:
        automatic_profile = (
            profiles_root / automatic_profile_name
            if collision_index == 1
            else profiles_root / f"{automatic_profile_name}-{collision_index}"
        )
        collision_index += 1
        if not automatic_profile.exists():
            try:
                create_private_credential_profile(
                    source=active_credential,
                    profile_directory=automatic_profile,
                    support=support,
                )
            except ProfilePublicationConflictError:
                pass
            else:
                return automatic_profile

        concurrent_credential = profile_credential(profile_directory=automatic_profile, support=support)
        if not concurrent_credential.is_file():
            continue
        concurrent_identity = identity_reader(concurrent_credential)
        if concurrent_identity != active_identity:
            continue
        copy_private_credential(source=active_credential, destination=concurrent_credential)
        return automatic_profile
