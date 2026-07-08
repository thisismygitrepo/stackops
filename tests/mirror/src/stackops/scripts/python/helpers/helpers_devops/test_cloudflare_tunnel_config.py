from typing import cast

import pytest
import yaml

from stackops.scripts.python.helpers.helpers_devops.cloudflare_tunnel_config import merge_ingress_routes


def test_merge_ingress_routes_preserves_target_identity_and_unselected_routes() -> None:
    source = """
tunnel: source-tunnel
credentials-file: /source/credentials.json
ingress:
  - hostname: a.example.com
    service: ssh://10.0.0.1:22
  - hostname: b.example.com
    service: ssh://10.0.0.2:22
  - service: http_status:404
"""
    target = """
tunnel: target-tunnel
credentials-file: /target/credentials.json
ingress:
  - hostname: local.example.com
    service: ssh://192.168.0.2:22
  - hostname: a.example.com
    service: ssh://192.168.0.3:22
  - service: http_status:404
protocol: http2
"""

    merged_text = merge_ingress_routes(source, target, hostnames=("a.example.com", "b.example.com"))
    loaded: object = yaml.safe_load(merged_text)
    assert isinstance(loaded, dict)
    merged = cast(dict[str, object], loaded)
    ingress = cast(list[dict[str, object]], merged["ingress"])

    assert merged["tunnel"] == "target-tunnel"
    assert merged["credentials-file"] == "/target/credentials.json"
    assert merged["protocol"] == "http2"
    assert [route.get("hostname") for route in ingress] == ["local.example.com", "a.example.com", "b.example.com", None]
    assert ingress[1]["service"] == "ssh://10.0.0.1:22"


def test_merge_ingress_routes_rejects_missing_source_route() -> None:
    configuration = """
ingress:
  - hostname: present.example.com
    service: ssh://127.0.0.1:22
  - service: http_status:404
"""

    with pytest.raises(ValueError, match="missing routes: absent.example.com"):
        merge_ingress_routes(configuration, configuration, hostnames=("absent.example.com",))
