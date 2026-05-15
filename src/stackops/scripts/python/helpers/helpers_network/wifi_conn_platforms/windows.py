import subprocess
from pathlib import Path

from stackops.scripts.python.helpers.helpers_network.wifi_conn_platforms.common import (
    WifiNetwork,
    console,
    deduplicate_networks,
    run_text_command,
)


def get_available_networks() -> list[WifiNetwork]:
    networks: list[WifiNetwork] = []

    try:
        result = run_text_command(["netsh", "wlan", "show", "profiles"], check=True)

        for line in result.stdout.splitlines():
            if "All User Profile" not in line:
                continue
            _, raw_ssid = line.split(":", maxsplit=1)
            networks.append({"ssid": raw_ssid.strip(), "signal": "Unknown"})

        result = run_text_command(["netsh", "wlan", "show", "networks"], check=True)
        current_ssid: str | None = None

        for line in result.stdout.splitlines():
            if "SSID" in line and "BSSID" not in line:
                _, raw_ssid = line.split(":", maxsplit=1)
                current_ssid = raw_ssid.strip()
                continue
            if "Signal" in line and current_ssid is not None:
                _, raw_signal = line.split(":", maxsplit=1)
                networks.append({"ssid": current_ssid, "signal": raw_signal.strip()})
                current_ssid = None
    except subprocess.CalledProcessError as error:
        console.print(f"[red]❌ Error scanning networks: {error}[/red]")
    except Exception as error:
        console.print(f"[red]❌ Unexpected error: {error}[/red]")

    return deduplicate_networks(networks)


def connect(name: str, ssid: str) -> None:
    console.print(f"\n[blue]🌐 Connecting to network: {name} (SSID: {ssid})[/blue]")

    try:
        run_text_command(["netsh", "wlan", "connect", f"name={name}", f"ssid={ssid}", "interface=Wi-Fi"], check=True)
        console.print("[green]✅ Connected successfully![/green]\n")
    except subprocess.CalledProcessError as error:
        console.print(f"[red]❌ Error connecting: {error}[/red]")
        raise
    except Exception as error:
        console.print(f"[red]❌ Unexpected error: {error}[/red]")
        raise


def connect_to_new_network(ssid: str, password: str) -> None:
    try:
        create_new_connection(ssid, ssid, password)
        connect(ssid, ssid)
    except Exception as error:
        console.print(f"[red]❌ Failed to connect to {ssid}: {error}[/red]")
        raise


def display_available_networks() -> None:
    console.print("\n[blue]📡 Scanning for available networks...[/blue]")

    try:
        subprocess.run(["netsh", "wlan", "show", "networks", "interface=Wi-Fi"], check=True)
        console.print("[green]✅ Network scan completed![/green]\n")
    except subprocess.CalledProcessError as error:
        console.print(f"[red]❌ Error scanning networks: {error}[/red]")
    except Exception as error:
        console.print(f"[red]❌ Unexpected error: {error}[/red]")


def get_current_wifi_name() -> str:
    console.print("\n[blue]🔍 Checking current WiFi connection...[/blue]")

    try:
        result = run_text_command(["netsh", "wlan", "show", "interface"], check=True)

        for line in result.stdout.splitlines():
            if "SSID" not in line or "BSSID" in line:
                continue
            _, raw_wifi_name = line.split(":", maxsplit=1)
            wifi_name = raw_wifi_name.strip()
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
    profile_path = Path(f"{name}.xml")

    xml_config = f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{name}</name>
    <SSIDConfig>
        <SSID>
            <name>{ssid}</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>WPA2PSK</authentication>
                <encryption>AES</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
            <sharedKey>
                <keyType>passPhrase</keyType>
                <protected>false</protected>
                <keyMaterial>{password}</keyMaterial>
            </sharedKey>
        </security>
    </MSM>
</WLANProfile>"""

    try:
        profile_path.write_text(xml_config, encoding="utf-8")
        run_text_command(
            ["netsh", "wlan", "add", "profile", f"filename={profile_path}", "interface=Wi-Fi"],
            check=True,
        )
        console.print("[green]✅ Connection created successfully![/green]\n")
    except subprocess.CalledProcessError as error:
        console.print(f"[red]❌ Error creating connection: {error}[/red]")
        raise
    except Exception as error:
        console.print(f"[red]❌ Unexpected error: {error}[/red]")
        raise
    finally:
        profile_path.unlink(missing_ok=True)