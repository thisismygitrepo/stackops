from stackops.scripts.python.helpers.helpers_cloud.cloud_path_resolver import ES


def split_backup_remote_spec(value: str) -> tuple[str, str] | None:
    if ":" not in value or (len(value) > 1 and value[1] == ":"):
        return None
    cloud_name, remote_value = value.split(":", 1)
    if not cloud_name or not remote_value:
        return None
    return cloud_name, remote_value


def backup_path_needs_default_cloud(path_cloud: str | None) -> bool:
    if path_cloud in (None, ES):
        return True
    return split_backup_remote_spec(path_cloud) is None
