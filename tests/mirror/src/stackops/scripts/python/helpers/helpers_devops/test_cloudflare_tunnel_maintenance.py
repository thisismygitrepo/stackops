from stackops.scripts.python.helpers.helpers_devops.cloudflare_tunnel_maintenance import build_connector_update_script


def test_build_connector_update_script_handles_successful_update_exit_code_and_restart_delay() -> None:
    script = build_connector_update_script(cloudflared_binary="~/.local/bin/cloudflared", service_name="cloudflared", timeout_seconds=60)

    assert 'readonly cloudflared_binary="$HOME"/.local/bin/cloudflared' in script
    assert "update_status != 0 && update_status != 11" in script
    assert "for _attempt in {1..30}" in script
    assert 'systemctl is-active --quiet "$service_name"' in script
