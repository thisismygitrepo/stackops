import re
from pathlib import Path

from stackops.profile.dotfiles_mapper import ALL_OS_VALUES, OsName
from stackops.scripts.python.helpers.helpers_cloud.cloud_path_resolver import ES
from stackops.scripts.python.helpers.helpers_cloud.backup_config import (
    BackupConfig,
    USER_BACKUP_PATH,
    VALID_OS,
    describe_missing_backup_config,
    read_user_backup_config_for_update,
    write_backup_config,
)
from stackops.utils.cloud.encryption import EncryptionMode, EncryptionModeChoice, parse_encryption_mode


def sanitize_entry_name(value: str) -> str:
    token = value.strip().replace(".", "_").replace("-", "_")
    token = re.sub(r"\s+", "_", token)
    token = re.sub(r"[^A-Za-z0-9_]", "_", token)
    return token or "backup_item"


def all_os_values(os_values: set[OsName]) -> bool:
    return len(os_values) == len(ALL_OS_VALUES) and all(value in os_values for value in ALL_OS_VALUES)


def _require_os_name(value: str, *, os_filter: str) -> OsName:
    token = value.strip().lower()
    if token not in VALID_OS:
        raise ValueError(f"Invalid os value: {os_filter!r}. Expected one of: {sorted(VALID_OS)}")
    return token


def register_backup_entry(
    *,
    path_local: str,
    group: str,
    entry_name: str | None,
    path_cloud: str | None,
    share_url: str | None,
    zip_: bool,
    encryption: EncryptionModeChoice | None,
    password: str | None,
    rel2home: bool | None,
    os: str,
) -> tuple[Path, str, bool]:
    local_path = Path(path_local).expanduser().absolute()
    if not local_path.exists():
        raise ValueError(f"Local path does not exist: {local_path}")
    os_parts = [part.strip() for part in os.split(",")]
    os_tokens_unsorted: set[OsName] = set()
    for part in os_parts:
        if not part:
            continue
        os_tokens_unsorted.add(_require_os_name(part, os_filter=os))
    os_tokens = sorted(os_tokens_unsorted, key=ALL_OS_VALUES.index)
    if not os_tokens:
        raise ValueError(f"Invalid os value: {os!r}. Expected one of: {sorted(VALID_OS)}")

    home = Path.home()
    in_home = local_path.is_relative_to(home)
    resolved_rel2home = in_home if rel2home is None else rel2home
    if resolved_rel2home and not in_home:
        raise ValueError("rel2home is true, but the local path is not under the home directory.")

    group_name = sanitize_entry_name(group) if group and group.strip() else "default"
    if entry_name is None or not entry_name.strip():
        base_name = sanitize_entry_name(local_path.stem)
        resolved_entry_name = base_name if all_os_values(set(os_tokens)) else f"{base_name}_{'_'.join(os_tokens)}"
    else:
        resolved_entry_name = sanitize_entry_name(entry_name)

    local_display = f"~/{local_path.relative_to(home)}" if resolved_rel2home and in_home else local_path.as_posix()
    cloud_value = path_cloud.strip() if path_cloud and path_cloud.strip() else ES
    share_url_value = share_url.strip() if share_url and share_url.strip() else None

    encryption_mode: EncryptionMode | None = None if encryption is None else parse_encryption_mode(encryption, label="Encryption mode")
    if password is not None:
        if password == "":
            raise ValueError("Password must be non-empty.")
        if encryption_mode != "symmetric":
            raise ValueError("Password requires encryption mode symmetric.")

    USER_BACKUP_PATH.parent.mkdir(parents=True, exist_ok=True)
    if USER_BACKUP_PATH.exists():
        existing_config = read_user_backup_config_for_update()
        if existing_config is None:
            raise ValueError(describe_missing_backup_config(source="user"))
        config = existing_config
    else:
        config: BackupConfig = {}

    if group_name in config:
        group_entries = config[group_name]
    else:
        group_entries = {}
        config[group_name] = group_entries
    replaced = resolved_entry_name in group_entries
    group_entries[resolved_entry_name] = {
        "path_local": local_display,
        "path_cloud": cloud_value,
        "share_url": share_url_value,
        "zip": zip_,
        "encryption": encryption_mode,
        "rel2home": resolved_rel2home,
        "os": set(os_tokens),
    }
    write_backup_config(USER_BACKUP_PATH, config)
    return USER_BACKUP_PATH, resolved_entry_name, replaced
