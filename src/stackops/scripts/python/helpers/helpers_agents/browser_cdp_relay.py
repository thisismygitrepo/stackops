import argparse
import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
import sys
from typing import cast

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import (
    BROWSER_RELAY_STARTUP_GRACE_SECONDS,
    BROWSER_RELAY_TARGET_PROBE_INTERVAL_SECONDS,
    BROWSER_RELAY_TARGET_PROBE_TIMEOUT_SECONDS,
    BROWSER_RELAY_TARGET_UNAVAILABLE_GRACE_SECONDS,
)


@dataclass(frozen=True)
class RelayConfig:
    listen_host: str
    listen_port: int
    target_host: str
    target_port: int


async def run_relay(*, config: RelayConfig) -> None:
    server = await asyncio.start_server(lambda reader, writer: _handle_client(reader=reader, writer=writer, config=config), config.listen_host, config.listen_port)
    async with server:
        await _wait_until_target_unavailable(config=config)


async def _wait_until_target_unavailable(*, config: RelayConfig) -> None:
    event_loop = asyncio.get_running_loop()
    startup_deadline = event_loop.time() + BROWSER_RELAY_STARTUP_GRACE_SECONDS
    target_was_available = False
    unavailable_since: float | None = None
    while True:
        probe_started_at = event_loop.time()
        if await _target_is_available(config=config):
            target_was_available = True
            unavailable_since = None
        elif not target_was_available and probe_started_at >= startup_deadline:
            return
        elif unavailable_since is None:
            unavailable_since = probe_started_at
        elif target_was_available and probe_started_at - unavailable_since >= BROWSER_RELAY_TARGET_UNAVAILABLE_GRACE_SECONDS:
            return
        await asyncio.sleep(BROWSER_RELAY_TARGET_PROBE_INTERVAL_SECONDS)


async def _target_is_available(*, config: RelayConfig) -> bool:
    try:
        async with asyncio.timeout(BROWSER_RELAY_TARGET_PROBE_TIMEOUT_SECONDS):
            _target_reader, target_writer = await asyncio.open_connection(config.target_host, config.target_port)
    except (OSError, TimeoutError):
        return False
    target_writer.close()
    await target_writer.wait_closed()
    return True


async def _handle_client(*, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, config: RelayConfig) -> None:
    try:
        target_reader, target_writer = await asyncio.open_connection(config.target_host, config.target_port)
    except OSError:
        writer.close()
        await writer.wait_closed()
        return

    try:
        await asyncio.gather(
            _pipe(reader=reader, writer=target_writer),
            _pipe(reader=target_reader, writer=writer),
        )
    finally:
        target_writer.close()
        writer.close()
        await target_writer.wait_closed()
        await writer.wait_closed()


async def _pipe(*, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    while True:
        data = await reader.read(65_536)
        if len(data) == 0:
            return
        writer.write(data)
        await writer.drain()


def parse_relay_config(*, argv: Sequence[str]) -> RelayConfig:
    parser = argparse.ArgumentParser(prog="stackops-cdp-relay")
    parser.add_argument("--listen-host", required=True)
    parser.add_argument("--listen-port", required=True, type=int)
    parser.add_argument("--target-host", required=True)
    parser.add_argument("--target-port", required=True, type=int)
    namespace = parser.parse_args(argv)
    return RelayConfig(
        listen_host=cast(str, namespace.listen_host),
        listen_port=cast(int, namespace.listen_port),
        target_host=cast(str, namespace.target_host),
        target_port=cast(int, namespace.target_port),
    )


def main() -> None:
    config = parse_relay_config(argv=sys.argv[1:])
    asyncio.run(run_relay(config=config))


if __name__ == "__main__":
    main()
