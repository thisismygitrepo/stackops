import subprocess
from dataclasses import dataclass

from stackops.scripts.python.helpers.helpers_network.wifi_conn_platforms.common import (
    WifiNetwork,
    console,
    deduplicate_networks,
    render_networks_table,
    run_text_command,
)


@dataclass(frozen=True)
class LinuxWifiDevice:
    name: str
    state: str


def _split_nmcli_fields(raw_line: str, *, field_count: int) -> list[str]:
    fields: list[str] = []
    current_chars: list[str] = []
    is_escaped = False

    for char in raw_line:
        if is_escaped:
            current_chars.append(char)
            is_escaped = False
            continue
        if char == "\\":
            is_escaped = True
            continue
        if char == ":" and len(fields) < field_count - 1:
            fields.append("".join(current_chars))
            current_chars = []
            continue
        current_chars.append(char)

    if is_escaped:
        current_chars.append("\\")
    fields.append("".join(current_chars))
    return fields


def _parse_linux_wifi_scan_output(stdout: str) -> list[WifiNetwork]:
    networks: list[WifiNetwork] = []
    for line in stdout.splitlines():
        if line == "":
            continue
        ssid, signal = _split_nmcli_fields(line, field_count=2)
        if ssid == "":
            continue
        networks.append({"ssid": ssid.strip(), "signal": f"{signal.strip()}%"})
    return networks


def _parse_linux_wifi_devices_output(stdout: str) -> list[LinuxWifiDevice]:
    devices: list[LinuxWifiDevice] = []
    for line in stdout.splitlines():
        if line == "":
            continue
        fields = _split_nmcli_fields(line, field_count=3)
        if len(fields) != 3:
            continue
        device_name, device_kind, device_state = fields
        if device_kind != "wifi" or device_name == "":
            continue
        devices.append(LinuxWifiDevice(name=device_name, state=device_state))
    return devices


def _get_linux_wifi_devices() -> list[LinuxWifiDevice]:
    result = run_text_command(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device", "status"], check=True)
    return _parse_linux_wifi_devices_output(result.stdout)


def _get_linux_wifi_device(device_name: str) -> LinuxWifiDevice:
    for device in _get_linux_wifi_devices():
        if device.name == device_name:
            return device
    raise RuntimeError(f"WiFi device '{device_name}' is no longer visible to NetworkManager")


def _select_linux_wifi_device(devices: list[LinuxWifiDevice]) -> LinuxWifiDevice:
    managed_devices = [device for device in devices if device.state != "unmanaged"]
    if len(managed_devices) > 0:
        return managed_devices[0]
    return devices[0]


def _ensure_linux_wifi_radio_enabled() -> None:
    result = run_text_command(["nmcli", "radio", "wifi"], check=True)
    radio_state = result.stdout.strip().lower()
    if radio_state == "enabled":
        return
    if radio_state != "disabled":
        raise RuntimeError(f"Unexpected WiFi radio state reported by NetworkManager: {radio_state or '<empty>'}")
    console.print("[yellow]⚠️  WiFi radio is disabled, enabling it via NetworkManager...[/yellow]")
    run_text_command(["nmcli", "radio", "wifi", "on"], check=True)


def _ensure_linux_wifi_device_managed(device: LinuxWifiDevice) -> LinuxWifiDevice:
    if device.state != "unmanaged":
        return device

    console.print(f"[yellow]⚠️  WiFi device '{device.name}' is unmanaged, asking NetworkManager to take control...[/yellow]")
    result = run_text_command(["nmcli", "device", "set", device.name, "managed", "yes"], check=False)
    if result.returncode != 0:
        error_text = result.stderr.strip() or result.stdout.strip() or "Unknown nmcli error"
        raise RuntimeError(f"NetworkManager could not manage WiFi device '{device.name}': {error_text}")

    refreshed_device = _get_linux_wifi_device(device.name)
    if refreshed_device.state == "unmanaged":
        raise RuntimeError(f"WiFi device '{device.name}' is still unmanaged after the recovery attempt")
    return refreshed_device


def _ensure_linux_wifi_ready() -> str:
    devices = _get_linux_wifi_devices()
    if len(devices) == 0:
        raise RuntimeError("No WiFi adapter was detected by NetworkManager")

    _ensure_linux_wifi_radio_enabled()
    device = _get_linux_wifi_device(_select_linux_wifi_device(devices).name)
    device = _ensure_linux_wifi_device_managed(device)
    if device.state == "unavailable":
        raise RuntimeError(f"WiFi device '{device.name}' is unavailable")
    return device.name


def get_available_networks() -> list[WifiNetwork]:
    networks: list[WifiNetwork] = []

    try:
        device_name = _ensure_linux_wifi_ready()
        run_text_command(["nmcli", "device", "wifi", "rescan"], check=True)
        result = run_text_command(
            ["nmcli", "-t", "-f", "SSID,SIGNAL", "device", "wifi", "list", "ifname", device_name],
            check=True,
        )
        networks = _parse_linux_wifi_scan_output(result.stdout)
        if len(networks) == 0:
            console.print(
                f"[yellow]⚠️  WiFi scan completed on '{device_name}', but NetworkManager did not report any visible networks[/yellow]"
            )
    except subprocess.CalledProcessError as error:
        console.print(f"[red]❌ Error scanning networks: {error}[/red]")
    except Exception as error:
        console.print(f"[red]❌ Unexpected error: {error}[/red]")

    return deduplicate_networks(networks)


def connect(name: str, ssid: str) -> None:
    console.print(f"\n[blue]🌐 Connecting to network: {name} (SSID: {ssid})[/blue]")

    try:
        device_name = _ensure_linux_wifi_ready()
        subprocess.run(["nmcli", "connection", "up", "id", name, "ifname", device_name], check=True)
        console.print("[green]✅ Connected successfully![/green]\n")
    except subprocess.CalledProcessError as error:
        console.print(f"[red]❌ Error connecting: {error}[/red]")
        raise
    except Exception as error:
        console.print(f"[red]❌ Unexpected error: {error}[/red]")
        raise


def connect_to_new_network(ssid: str, password: str) -> None:
    try:
        device_name = _ensure_linux_wifi_ready()
        try:
            subprocess.run(["nmcli", "device", "wifi", "connect", ssid, "password", password, "ifname", device_name], check=True)
            console.print("[green]✅ Connected successfully![/green]\n")
        except subprocess.CalledProcessError:
            create_new_connection(ssid, ssid, password)
            connect(ssid, ssid)
    except Exception as error:
        console.print(f"[red]❌ Failed to connect to {ssid}: {error}[/red]")
        raise


def display_available_networks() -> None:
    console.print("\n[blue]📡 Scanning for available networks...[/blue]")
    networks = get_available_networks()
    if len(networks) == 0:
        console.print("[yellow]⚠️  No visible WiFi networks were reported[/yellow]")
        return
    render_networks_table(networks, title="Available WiFi Networks")
    console.print("[green]✅ Network scan completed![/green]\n")


def get_current_wifi_name() -> str:
    console.print("\n[blue]🔍 Checking current WiFi connection...[/blue]")

    try:
        result = subprocess.run(["iwgetid", "-r"], capture_output=True, text=True, check=True)
        wifi_name = result.stdout.strip()
        if wifi_name != "":
            console.print(f"[green]✅ Connected to: {wifi_name}[/green]\n")
            return wifi_name
        console.print("[yellow]⚠️  Not connected to WiFi[/yellow]\n")
        return "Not connected to WiFi"
    except subprocess.CalledProcessError:
        console.print("[yellow]⚠️  Not connected to WiFi or unable to detect[/yellow]\n")
        return "Not connected to WiFi"
    except Exception as error:
        console.print(f"[red]❌ Error: {error}[/red]\n")
        return "Error detecting WiFi"


def create_new_connection(name: str, ssid: str, password: str) -> None:
    console.print(f"\n[blue]🔧 Creating new connection: {name} (SSID: {ssid})[/blue]")

    try:
        device_name = _ensure_linux_wifi_ready()
        check_result = run_text_command(["nmcli", "connection", "show", name], check=False)

        if check_result.returncode == 0:
            console.print(f"[yellow]⚠️  Connection '{name}' already exists, deleting old one...[/yellow]")
            subprocess.run(["nmcli", "connection", "delete", name], check=True)

        subprocess.run(
            [
                "nmcli",
                "connection",
                "add",
                "type",
                "wifi",
                "con-name",
                name,
                "ifname",
                device_name,
                "ssid",
                ssid,
                "wifi-sec.key-mgmt",
                "wpa-psk",
                "wifi-sec.psk",
                password,
            ],
            check=True,
        )

        console.print("[green]✅ Connection created successfully![/green]\n")
    except subprocess.CalledProcessError as error:
        console.print(f"[red]❌ Error creating connection: {error}[/red]")
        raise
    except Exception as error:
        console.print(f"[red]❌ Unexpected error: {error}[/red]")
        raise