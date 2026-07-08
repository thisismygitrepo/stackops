import pytest

from stackops.scripts.python.helpers.helpers_devops.cloudflare_tunnel_runtime import parse_tunnel_health, validate_ssh_host


def test_parse_tunnel_health_aggregates_connectors_versions_and_sessions() -> None:
    raw_json = """
{
  "conns": [
    {"version": "2026.6.1", "conns": [{}, {}, {}, {}]},
    {"version": "2026.6.1", "conns": [{}, {}, {}]},
    {"version": "2026.5.0", "conns": [{}]}
  ]
}
"""

    health = parse_tunnel_health(raw_json)

    assert health.connector_count == 3
    assert health.edge_session_count == 8
    assert health.edge_sessions_per_connector == (1, 3, 4)
    assert health.versions == (("2026.5.0", 1), ("2026.6.1", 2))


@pytest.mark.parametrize("host", ["host name", "host;rm", "$(command)", "host/path"])
def test_validate_ssh_host_rejects_shell_syntax(host: str) -> None:
    with pytest.raises(ValueError, match="Invalid SSH host"):
        validate_ssh_host(host)
