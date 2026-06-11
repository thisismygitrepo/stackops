import string
from dataclasses import dataclass
from typing import Protocol, TypedDict, cast


class CountryFlag(TypedDict, total=False):
    emoji: str
    unicode: str


class CountryCurrency(TypedDict, total=False):
    code: str
    symbol: str


class Continent(TypedDict, total=False):
    code: str
    name: str


class PublicIpInfo(TypedDict, total=True):
    ip: str
    hostname: str
    city: str
    region: str
    country: str
    country_name: str
    country_flag: CountryFlag
    country_flag_url: str
    country_currency: CountryCurrency
    continent: Continent
    loc: str
    org: str
    postal: str
    timezone: str


@dataclass(frozen=True, slots=True)
class InterfaceIPv4Address:
    interface: str
    ipv4_address: str
    mac_address: str | None


class InterfaceAddressRecord(Protocol):
    family: int
    address: str
    broadcast: str | None


def get_public_ip_address() -> PublicIpInfo:
    from stackops.utils.installer_utils.installer_cli import install_if_missing

    install_if_missing(which="ipinfo", binary_name=None, verbose=True)
    import subprocess

    result = subprocess.run(["ipinfo", "myip", "--json"], check=True, capture_output=True, text=True, encoding="utf-8")
    import json

    loaded_json: PublicIpInfo = json.loads(result.stdout)
    return loaded_json


def _interface_link_families() -> set[int]:
    import psutil
    import socket

    family_candidates = (
        getattr(psutil, "AF_LINK", None),
        getattr(socket, "AF_LINK", None),
        getattr(socket, "AF_PACKET", None),
    )
    return {family for family in family_candidates if isinstance(family, int)}


def _normalize_mac_address(raw_address: str) -> str | None:
    normalized = raw_address.strip().replace("-", ":").lower()
    if not normalized:
        return None
    octets = normalized.split(":")
    if len(octets) != 6:
        return None
    padded_octets: list[str] = []
    for octet in octets:
        if not 1 <= len(octet) <= 2:
            return None
        if any(character not in string.hexdigits for character in octet):
            return None
        padded_octets.append(octet.zfill(2))
    normalized_mac_address = ":".join(padded_octets)
    if normalized_mac_address == "00:00:00:00:00:00":
        return None
    return normalized_mac_address


def _get_interface_addresses() -> dict[str, list[InterfaceAddressRecord]]:
    import psutil

    return {
        iface: cast(list[InterfaceAddressRecord], addrs)
        for iface, addrs in psutil.net_if_addrs().items()
    }


def _extract_mac_address(addrs: list[InterfaceAddressRecord]) -> str | None:
    link_families = _interface_link_families()
    for addr in addrs:
        if addr.family not in link_families:
            continue
        normalized_mac_address = _normalize_mac_address(addr.address)
        if normalized_mac_address is not None:
            return normalized_mac_address
    return None


def _build_interface_ipv4_addresses(interface_addresses: dict[str, list[InterfaceAddressRecord]]) -> list[InterfaceIPv4Address]:
    import socket

    interface_mac_addresses = {iface: _extract_mac_address(addrs) for iface, addrs in interface_addresses.items()}
    result: list[InterfaceIPv4Address] = []
    for iface, addrs in interface_addresses.items():
        for addr in addrs:
            if addr.family == socket.AF_INET and addr.address:
                result.append(
                    InterfaceIPv4Address(
                        interface=iface,
                        ipv4_address=addr.address,
                        mac_address=interface_mac_addresses[iface],
                    )
                )
    return result


def get_all_interface_ipv4_addresses() -> list[InterfaceIPv4Address]:
    return _build_interface_ipv4_addresses(_get_interface_addresses())


def get_all_ipv4_addresses() -> list[tuple[str, str]]:
    return [(address.interface, address.ipv4_address) for address in get_all_interface_ipv4_addresses()]


def select_lan_interface_ipv4(prefer_vpn: bool) -> InterfaceIPv4Address | None:
    """
    Choose the best 'real LAN' IPv4:
      - Excludes loopback/link-local and (by default) VPN/tunnel/container ifaces
      - Prefers physical-looking ifaces (eth/en*/wlan/wl*)
      - Prefers RFC1918 LANs: 192.168/16 > 10/8 > 172.16/12
      - Requires interface is UP
    Set prefer_vpn=True to allow tunnel/VPN ifaces to compete.
    """

    import ipaddress
    import re
    import socket
    from collections.abc import Sequence
    import psutil

    # Down-rank or exclude: tunnels/VPNs/bridges/containers (add your own if needed)
    VIRTUAL_IFACE_PAT = re.compile(
        r"^(?:lo|loopback|docker\d*|br-.*|veth.*|virbr.*|bridge.*|"
        r"vboxnet.*|vmnet.*|zt.*|ham.*|tailscale.*|wg\d*|utun\d*|llw\d*|awdl\d*|"
        r"tun\d*|tap\d*|cloudflarewarp.*|warp.*)$",
        re.IGNORECASE,
    )

    # Light preference for names that look like real NICs
    PHYSICAL_IFACE_PAT = re.compile(r"^(?:eth\d*|en\d*|enp.*|ens.*|eno.*|wlan\d*|wl.*|.*wifi.*|.*ethernet.*)$", re.IGNORECASE)

    # Known noisy CIDRs to avoid
    NOISY_NETS: list[ipaddress.IPv4Network] = [
        ipaddress.IPv4Network("100.64.0.0/10"),  # CGNAT (Tailscale/others)
        ipaddress.IPv4Network("172.17.0.0/16"),  # docker0 default
        ipaddress.IPv4Network("172.18.0.0/16"),
        ipaddress.IPv4Network("172.19.0.0/16"),
        ipaddress.IPv4Network("192.168.49.0/24"),  # minikube default
        ipaddress.IPv4Network("10.0.2.0/24"),  # VirtualBox NAT
    ]

    def _in_any(ip: ipaddress.IPv4Address, nets: Sequence[ipaddress.IPv4Network]) -> bool:
        return any(ip in n for n in nets)

    interface_addresses = _get_interface_addresses()
    all_ipv4_addresses = _build_interface_ipv4_addresses(interface_addresses)
    stats = psutil.net_if_stats()
    best: InterfaceIPv4Address | None = None
    best_score = float(-(10**9))

    for address in all_ipv4_addresses:
        st = stats.get(address.interface)
        if not st or not st.isup:
            continue

        try:
            ip = cast(ipaddress.IPv4Address, ipaddress.ip_address(address.ipv4_address))
        except ValueError:
            continue

        # Exclude unusable classes
        if ip.is_loopback or ip.is_link_local:  # 127.0.0.0/8, 169.254.0.0/16
            continue

        # Hard filter: if it looks virtual and we don't prefer VPNs, skip it
        if not prefer_vpn and VIRTUAL_IFACE_PAT.match(address.interface):
            continue

        # Hard filter: known noisy subnets (docker, cgnat, etc.)
        if _in_any(ip, NOISY_NETS) and not prefer_vpn:
            continue

        # Base score
        score: float = 0.0

        # Prefer physical-looking names
        if PHYSICAL_IFACE_PAT.match(address.interface):
            score += 200

        # Broadcast present usually means L2 LAN (not point-to-point)
        broadcast_present = any(
            interface_addr.family == socket.AF_INET
            and interface_addr.address == address.ipv4_address
            and interface_addr.broadcast is not None
            for interface_addr in interface_addresses.get(address.interface, [])
        )
        if broadcast_present:
            score += 100

        # Prefer private RFC1918; rank families
        if ip.is_private:
            # Order: 192.168.x.x > 10.x.x.x > 172.16-31.x.x
            ip_net = ipaddress.IPv4Network((ip, 32), strict=False)
            if ipaddress.IPv4Network("192.168.0.0/16").supernet_of(ip_net):
                score += 90
            elif ipaddress.IPv4Network("10.0.0.0/8").supernet_of(ip_net):
                score += 70
            elif ipaddress.IPv4Network("172.16.0.0/12").supernet_of(ip_net):
                score += 50
        else:
            # Public on a NIC is unusual for a home/office LAN
            score -= 50

        # Slight nudge by interface speed if known (>0 means psutil knows it)
        # (Many tunnels report 0)
        if getattr(st, "speed", 0) > 0:
            score += 20

        # Deterministic tie-breaker: prefer shorter iface name (eth0 over eth10)
        score -= len(address.interface) * 0.01

        if score > best_score:
            best_score = score
            best = address

    return best


def select_lan_ipv4(prefer_vpn: bool) -> str | None:
    selected_address = select_lan_interface_ipv4(prefer_vpn=prefer_vpn)
    if selected_address is None:
        return None
    return selected_address.ipv4_address


if __name__ == "__main__":
    print(select_lan_ipv4(False) or "No LAN IPv4 found")
