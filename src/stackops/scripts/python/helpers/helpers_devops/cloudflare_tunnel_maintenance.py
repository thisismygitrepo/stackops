from pathlib import Path
import secrets
import shlex
import subprocess
import tempfile

from stackops.scripts.python.helpers.helpers_devops.cloudflare_tunnel_config import merge_ingress_routes
from stackops.scripts.python.helpers.helpers_devops.cloudflare_tunnel_runtime import (
    read_host_file,
    require_success,
    run_host_command,
    validate_service_name,
    validate_ssh_host,
)


def _shell_value(value: str) -> str:
    if value.startswith("~/"):
        return f'"$HOME"/{shlex.quote(value[2:])}'
    return shlex.quote(value)


def build_connector_update_script(cloudflared_binary: str, service_name: str, timeout_seconds: int) -> str:
    validate_service_name(service_name)
    if timeout_seconds < 1:
        raise ValueError("Timeout must be at least one second.")
    attempts = (timeout_seconds + 1) // 2
    return f"""#!/usr/bin/env bash
set -euo pipefail
readonly cloudflared_binary={_shell_value(cloudflared_binary)}
readonly service_name={shlex.quote(service_name)}

sudo -v
set +e
sudo "$cloudflared_binary" update
update_status=$?
set -e
if (( update_status != 0 && update_status != 11 )); then
    printf 'cloudflared update failed with status %d.\n' "$update_status" >&2
    exit "$update_status"
fi

set +e
sudo systemctl restart "$service_name"
set -e
service_running=false
for _attempt in {{1..{attempts}}}; do
    if systemctl is-active --quiet "$service_name"; then
        service_running=true
        break
    fi
    sleep 2
done
if [[ "$service_running" != true ]]; then
    printf '%s did not become active within {timeout_seconds} seconds.\n' "$service_name" >&2
    exit 1
fi

"$cloudflared_binary" --version
"""


def rolling_update_connectors(hosts: tuple[str, ...], include_local: bool, cloudflared_binary: str, service_name: str, timeout_seconds: int) -> None:
    targets: list[str | None] = [None] if include_local else []
    for host in hosts:
        validate_ssh_host(host)
        targets.append(host)
    if len(targets) == 0:
        raise ValueError("Select the local connector or at least one SSH host.")

    script = build_connector_update_script(cloudflared_binary=cloudflared_binary, service_name=service_name, timeout_seconds=timeout_seconds)
    for target in targets:
        label = target or "local"
        print(f"Updating Cloudflare connector on {label}...")
        result = run_host_command(("bash", "-lc", script), host=target, capture_output=False, interactive=True, timeout_seconds=None)
        require_success(result, f"Updating Cloudflare connector on {label}")


def _build_route_install_script(
    staged_config: str, target_config: str, cloudflared_binary: str, service_name: str, timeout_seconds: int, transaction_id: str
) -> str:
    validate_service_name(service_name)
    if timeout_seconds < 1:
        raise ValueError("Timeout must be at least one second.")
    attempts = (timeout_seconds + 1) // 2
    rollback_config = f"{target_config}.stackops-{transaction_id}"
    return f"""#!/usr/bin/env bash
set -euo pipefail
readonly staged_config={_shell_value(staged_config)}
readonly target_config={_shell_value(target_config)}
readonly rollback_config={_shell_value(rollback_config)}
readonly cloudflared_binary={_shell_value(cloudflared_binary)}
readonly service_name={shlex.quote(service_name)}

sudo -v
"$cloudflared_binary" --config "$staged_config" tunnel ingress validate
target_owner="$(stat -c '%U' "$target_config")"
target_group="$(stat -c '%G' "$target_config")"
target_mode="$(stat -c '%a' "$target_config")"
sudo cp --preserve=mode,ownership,timestamps "$target_config" "$rollback_config"
rollback() {{
    sudo mv "$rollback_config" "$target_config"
    set +e
    sudo systemctl restart "$service_name"
    set -e
}}
trap 'if [[ -e "$rollback_config" ]]; then rollback; fi' EXIT

sudo install -o "$target_owner" -g "$target_group" -m "$target_mode" "$staged_config" "$target_config"
sudo "$cloudflared_binary" --config "$target_config" tunnel ingress validate
set +e
sudo systemctl restart "$service_name"
set -e

service_running=false
for _attempt in {{1..{attempts}}}; do
    if systemctl is-active --quiet "$service_name"; then
        service_running=true
        break
    fi
    sleep 2
done
if [[ "$service_running" != true ]]; then
    printf '%s did not become active within {timeout_seconds} seconds.\n' "$service_name" >&2
    exit 1
fi

sudo rm "$rollback_config"
trap - EXIT
"$cloudflared_binary" --version
"""


def _copy_staged_config(local_path: Path, target_host: str, remote_path: str) -> None:
    validate_ssh_host(target_host)
    result: subprocess.CompletedProcess[str] = subprocess.run(
        ("scp", "--", str(local_path), f"{target_host}:{remote_path}"), capture_output=True, text=True, check=False, timeout=30
    )
    require_success(result, f"Copying staged configuration to {target_host}")


def sync_ingress_routes(
    source_host: str | None,
    source_config: str,
    target_host: str | None,
    target_config: str,
    hostnames: tuple[str, ...],
    cloudflared_binary: str,
    service_name: str,
    timeout_seconds: int,
) -> None:
    source_text = read_host_file(source_host, source_config)
    target_text = read_host_file(target_host, target_config)
    merged_text = merge_ingress_routes(source_text=source_text, target_text=target_text, hostnames=hostnames)
    transaction_id = secrets.token_hex(6)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", encoding="utf-8", delete=False) as staged_file:
        staged_file.write(merged_text)
        local_staged_path = Path(staged_file.name)

    remote_staged_path: str | None = None
    try:
        if target_host is None:
            staged_config = str(local_staged_path)
        else:
            remote_staged_path = f"/tmp/stackops-cloudflared-{transaction_id}.yml"
            _copy_staged_config(local_staged_path, target_host=target_host, remote_path=remote_staged_path)
            staged_config = remote_staged_path

        script = _build_route_install_script(
            staged_config=staged_config,
            target_config=target_config,
            cloudflared_binary=cloudflared_binary,
            service_name=service_name,
            timeout_seconds=timeout_seconds,
            transaction_id=transaction_id,
        )
        result = run_host_command(("bash", "-lc", script), host=target_host, capture_output=False, interactive=True, timeout_seconds=None)
        require_success(result, f"Synchronizing routes on {target_host or 'local'}")
    finally:
        local_staged_path.unlink(missing_ok=True)
        if target_host is not None and remote_staged_path is not None:
            run_host_command(("rm", "-f", "--", remote_staged_path), host=target_host, capture_output=True, interactive=False, timeout_seconds=15)
