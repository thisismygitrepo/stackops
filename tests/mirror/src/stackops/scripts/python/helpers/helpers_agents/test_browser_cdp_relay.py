from stackops.scripts.python.helpers.helpers_agents.browser_cdp_relay import RelayConfig, parse_relay_config


def test_parse_relay_config_reads_required_endpoint_arguments() -> None:
    config = parse_relay_config(
        argv=(
            "--listen-host",
            "0.0.0.0",
            "--listen-port",
            "9331",
            "--target-host",
            "127.0.0.1",
            "--target-port",
            "41837",
        )
    )

    assert config == RelayConfig(
        listen_host="0.0.0.0",
        listen_port=9331,
        target_host="127.0.0.1",
        target_port=41837,
    )
