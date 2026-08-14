from stackops.utils.source_of_truth import DOTFILES_STACKOPS_CONFIG_PATH, read_stackops_config_string


class DefaultRcloneRemoteConfigError(ValueError):
    pass


def _default_remote_failure_reason(error: FileNotFoundError | KeyError | ValueError) -> str:
    if isinstance(error, FileNotFoundError):
        return "The StackOps config file does not exist."
    if isinstance(error, KeyError):
        return "The StackOps config does not define 'default_rclone_config'."
    return f"The StackOps config is invalid:\n{error}"


def read_default_rclone_remote() -> str:
    try:
        return read_stackops_config_string("default_rclone_config")
    except (FileNotFoundError, KeyError, ValueError) as exc:
        reason = _default_remote_failure_reason(error=exc)
        raise DefaultRcloneRemoteConfigError(
            "No default rclone remote is configured.\n"
            f"Reason: {reason}\n"
            f"Location: {DOTFILES_STACKOPS_CONFIG_PATH}\n\n"
            "Guided setup (selects a real rclone remote and writes the JSON + schema):\n"
            "  devops config setup cloud\n\n"
            "No rclone remote yet? Create one first:\n"
            "  rclone config"
        ) from exc
