import subprocess
import time

from stackops.scripts.python.helpers.helpers_network.address import get_public_ip_address


def _ip_is_acceptable(ip: str, current_ip: str | None, target_ip_addresses: list[str] | None) -> bool:
    if target_ip_addresses is not None:
        return ip in target_ip_addresses
    if current_ip and ip != current_ip:
        return True
    if current_ip is None:
        return True
    return False


def switch_public_ip_address(max_trials: int, wait_seconds: float, target_ip_addresses: list[str] | None) -> tuple[bool, str]:
    print("🔁 Switching IP ... ")
    from stackops.utils.installer_utils.installer_cli import install_if_missing
    install_if_missing(which="warp-cli", binary_name=None, verbose=True)

    current_ip: str | None = None
    try:
        current_data = get_public_ip_address()
        current_ip = current_data.get("ip")
    except Exception as e:
        print(f"⚠️ Could not get current IP: {e}")

    print(f"Current IP: {current_ip}")

    if target_ip_addresses is not None and current_ip and current_ip in target_ip_addresses:
        print(f"✅ Current IP {current_ip} is already in target list. No switch needed.")
        return True, current_ip

    latest_ip: str | None = current_ip
    for attempt in range(1, max_trials + 1):
        print(f"\n--- Attempt {attempt}/{max_trials} ---")

        print("🔻 Deactivating current connection ... ")
        subprocess.run(["warp-cli", "registration", "delete"], check=False)

        print(f"😴 Sleeping for {wait_seconds} seconds ... ")
        time.sleep(wait_seconds)

        print("🔼 Registering new connection ... ")
        res_reg = subprocess.run(["warp-cli", "registration", "new"], check=False)
        if res_reg.returncode != 0:
            print("⚠️ Registration failed, retrying loop...")
            continue

        print("🔗 Connecting ... ")
        subprocess.run(["warp-cli", "connect"], check=False)

        print(f"😴 Sleeping for {wait_seconds} seconds ... ")
        time.sleep(wait_seconds)

        print("🔍 Checking status of warp ... ")
        subprocess.run(["warp-cli", "status"], check=False)

        print("🔍 Checking new IP ... ")
        new_ip: str | None = None
        for ip_check_attempt in range(5):
            try:
                new_data = get_public_ip_address()
                new_ip = new_data["ip"]
                if new_ip:
                    break
            except Exception as e:
                print(f"⚠️ Error checking new IP (attempt {ip_check_attempt+1}/5): {e}")
                time.sleep(wait_seconds)

        latest_ip = new_ip or latest_ip
        if new_ip:
            print(f"New IP: {new_ip}")
            if _ip_is_acceptable(new_ip, current_ip, target_ip_addresses):
                print("✅ Done ... IP switched successfully.")
                return True, new_ip
            print("❌ IP not acceptable, retrying...")
        else:
            print("⚠️ Could not retrieve new IP after multiple attempts.")

    latest_ip = latest_ip or ""
    print("❌ Failed to switch IP after max trials.")
    return False, latest_ip

if __name__ == "__main__":
    switch_public_ip_address(max_trials=10, wait_seconds=4.0, target_ip_addresses=None)
