import base64
import binascii
import re
import shlex
import stat
from dataclasses import dataclass
from pathlib import Path

from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_common import SSHDSettings
from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_models import CheckStatus


PUBLIC_KEY_TYPE_PATTERN = re.compile(r"(?:ssh|ecdsa|sk-ssh|sk-ecdsa)-[A-Za-z0-9@._+-]+")


@dataclass(frozen=True, slots=True)
class KeyFileAssessment:
    status: CheckStatus
    message: str


def resolve_posix_authorized_key_paths(
    settings: SSHDSettings,
    home_directory: Path,
    user_name: str,
) -> tuple[Path, ...] | None:
    configured_values = settings.values.get("authorizedkeysfile", ())
    resolved: list[Path] = []
    for configured_value in configured_values:
        try:
            configured_paths = shlex.split(configured_value, comments=False, posix=True)
        except ValueError:
            return None
        for configured_path in configured_paths:
            if configured_path == "none":
                continue
            expanded = configured_path.replace("%%", "\0")
            expanded = expanded.replace("%h", str(home_directory)).replace("%u", user_name).replace("\0", "%")
            if "%" in expanded:
                return None
            path = Path(expanded)
            resolved.append(path if path.is_absolute() else home_directory.joinpath(path))
    return tuple(dict.fromkeys(resolved))


def assess_public_key_contents(path: Path) -> KeyFileAssessment:
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return KeyFileAssessment(status="error", message=f"{path} does not exist")
    except PermissionError:
        return KeyFileAssessment(status="error", message=f"{path} is not readable by the current user")
    except UnicodeDecodeError:
        return KeyFileAssessment(status="error", message=f"{path} is not valid UTF-8 text")
    except OSError as error:
        return KeyFileAssessment(status="unknown", message=f"Could not read {path}: {error}")

    active_records = [line.strip() for line in content.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    if not active_records:
        return KeyFileAssessment(status="error", message=f"{path} contains no public-key records")
    invalid_records = 0
    for record in active_records:
        try:
            tokens = shlex.split(record, comments=False, posix=True)
        except ValueError:
            invalid_records += 1
            continue
        key_index = next((index for index, token in enumerate(tokens) if PUBLIC_KEY_TYPE_PATTERN.fullmatch(token)), None)
        if key_index is None or key_index + 1 >= len(tokens):
            invalid_records += 1
            continue
        encoded_key = tokens[key_index + 1]
        encoded_key += "=" * (-len(encoded_key) % 4)
        try:
            decoded_key = base64.b64decode(encoded_key, validate=True)
        except (binascii.Error, ValueError):
            invalid_records += 1
            continue
        if len(decoded_key) < 16:
            invalid_records += 1
    if invalid_records:
        return KeyFileAssessment(
            status="error",
            message=f"{path} has {invalid_records} invalid record(s) out of {len(active_records)}",
        )
    return KeyFileAssessment(status="ok", message=f"{path} contains {len(active_records)} valid public key(s)")


def assess_posix_authorized_keys(
    paths: tuple[Path, ...] | None,
    home_directory: Path,
    user_id: int,
    authorized_keys_command: tuple[str, ...],
) -> KeyFileAssessment:
    if paths is None:
        return KeyFileAssessment(status="unknown", message="Effective AuthorizedKeysFile paths could not be resolved")
    if not paths:
        if any(command != "none" for command in authorized_keys_command):
            return KeyFileAssessment(
                status="unknown",
                message="Public keys are supplied by AuthorizedKeysCommand rather than a verifiable key file",
            )
        return KeyFileAssessment(status="error", message="Effective sshd settings configure no AuthorizedKeysFile")

    missing_paths: list[str] = []
    errors: list[str] = []
    unknowns: list[str] = []
    valid_files: list[str] = []
    for path in paths:
        try:
            file_stat = path.lstat()
        except FileNotFoundError:
            missing_paths.append(str(path))
            continue
        except PermissionError:
            unknowns.append(f"Permission denied while inspecting {path}")
            continue
        except OSError as error:
            unknowns.append(f"Could not inspect {path}: {error}")
            continue
        if not stat.S_ISREG(file_stat.st_mode):
            errors.append(f"{path} is not a regular file")
            continue
        if file_stat.st_uid not in (0, user_id):
            errors.append(f"{path} is owned by UID {file_stat.st_uid}, not root or UID {user_id}")
            continue
        if file_stat.st_mode & 0o022:
            errors.append(f"{path} is writable by its group or other users (mode {stat.S_IMODE(file_stat.st_mode):04o})")
            continue

        directories = [home_directory]
        try:
            relative_parent = path.parent.relative_to(home_directory)
        except ValueError:
            directories = list(reversed((path.parent, *path.parent.parents)))
        else:
            current_directory = home_directory
            for part in relative_parent.parts:
                current_directory = current_directory.joinpath(part)
                directories.append(current_directory)
        insecure_directory: str | None = None
        for directory in dict.fromkeys(directories):
            try:
                directory_stat = directory.lstat()
            except FileNotFoundError:
                errors.append(f"Directory {directory} does not exist")
                insecure_directory = "unknown"
                break
            except PermissionError as error:
                unknowns.append(f"Could not inspect directory {directory}: {error}")
                insecure_directory = "unknown"
                break
            except OSError as error:
                unknowns.append(f"Could not inspect directory {directory}: {error}")
                insecure_directory = "unknown"
                break
            if not stat.S_ISDIR(directory_stat.st_mode):
                insecure_directory = f"{directory} is not a directory"
                break
            if directory_stat.st_uid not in (0, user_id):
                insecure_directory = f"{directory} is owned by UID {directory_stat.st_uid}, not root or UID {user_id}"
                break
            if directory_stat.st_mode & 0o022:
                insecure_directory = (
                    f"{directory} is writable by its group or other users (mode {stat.S_IMODE(directory_stat.st_mode):04o})"
                )
                break
        if insecure_directory is not None:
            if insecure_directory != "unknown":
                errors.append(insecure_directory)
            continue

        content_assessment = assess_public_key_contents(path)
        if content_assessment.status == "ok":
            valid_files.append(content_assessment.message)
        elif content_assessment.status == "error":
            errors.append(content_assessment.message)
        else:
            unknowns.append(content_assessment.message)
    if errors:
        return KeyFileAssessment(status="error", message="; ".join(errors))
    if unknowns:
        return KeyFileAssessment(status="unknown", message="; ".join(unknowns))
    if valid_files:
        return KeyFileAssessment(status="ok", message="; ".join(valid_files))
    return KeyFileAssessment(status="error", message=f"No configured key file exists: {', '.join(missing_paths)}")
