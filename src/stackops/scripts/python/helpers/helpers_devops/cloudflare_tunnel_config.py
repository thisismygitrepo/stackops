from copy import deepcopy
from dataclasses import dataclass
from typing import cast

import yaml


@dataclass(frozen=True)
class IngressRoute:
    hostname: str | None
    service: str
    values: dict[str, object]


def _string_key_mapping(value: object, description: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{description} must be a mapping.")
    raw_mapping = cast(dict[object, object], value)
    if not all(isinstance(key, str) for key in raw_mapping):
        raise ValueError(f"{description} keys must be strings.")
    return {cast(str, key): item for key, item in raw_mapping.items()}


def _load_configuration(text: str, description: str) -> dict[str, object]:
    loaded: object = yaml.safe_load(text)
    configuration = _string_key_mapping(loaded, description)
    if "ingress" not in configuration:
        raise ValueError(f"{description} has no ingress routes.")
    return configuration


def _parse_routes(configuration: dict[str, object], description: str) -> list[IngressRoute]:
    raw_ingress = configuration["ingress"]
    if not isinstance(raw_ingress, list):
        raise ValueError(f"{description} ingress must be a list.")

    routes: list[IngressRoute] = []
    for index, raw_route in enumerate(cast(list[object], raw_ingress)):
        values = _string_key_mapping(raw_route, f"{description} ingress route {index}")
        hostname_raw = values.get("hostname")
        service_raw = values.get("service")
        if hostname_raw is not None and not isinstance(hostname_raw, str):
            raise ValueError(f"{description} ingress route {index} hostname must be a string.")
        if not isinstance(service_raw, str):
            raise ValueError(f"{description} ingress route {index} service must be a string.")
        routes.append(IngressRoute(hostname=hostname_raw, service=service_raw, values=values))
    return routes


def merge_ingress_routes(source_text: str, target_text: str, hostnames: tuple[str, ...]) -> str:
    if len(hostnames) == 0:
        raise ValueError("At least one hostname is required.")
    if len(set(hostnames)) != len(hostnames):
        raise ValueError("Hostnames must be unique.")

    source_configuration = _load_configuration(source_text, "Source configuration")
    target_configuration = _load_configuration(target_text, "Target configuration")
    source_routes = _parse_routes(source_configuration, "Source configuration")
    target_routes = _parse_routes(target_configuration, "Target configuration")

    source_by_hostname: dict[str, IngressRoute] = {}
    for route in source_routes:
        if route.hostname is None:
            continue
        if route.hostname in source_by_hostname:
            raise ValueError(f"Source configuration contains duplicate hostname {route.hostname!r}.")
        source_by_hostname[route.hostname] = route

    missing_hostnames = [hostname for hostname in hostnames if hostname not in source_by_hostname]
    if missing_hostnames:
        raise ValueError(f"Source configuration is missing routes: {', '.join(missing_hostnames)}.")

    catch_all_routes = [route for route in target_routes if route.hostname is None]
    if len(catch_all_routes) != 1:
        raise ValueError("Target configuration must contain exactly one catch-all route.")

    requested_hostnames = set(hostnames)
    retained_routes = [route for route in target_routes if route.hostname is not None and route.hostname not in requested_hostnames]
    copied_routes = [source_by_hostname[hostname] for hostname in hostnames]
    merged_routes = [*retained_routes, *copied_routes, catch_all_routes[0]]

    merged_configuration = deepcopy(target_configuration)
    merged_configuration["ingress"] = [deepcopy(route.values) for route in merged_routes]
    return yaml.safe_dump(merged_configuration, sort_keys=False, allow_unicode=True)
