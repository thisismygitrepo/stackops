import argparse
import subprocess
import sys
import time

from stackops.scripts.python.helpers.helpers_sessions._zellij_backend_state import run_zellij


def _client_panes(session_name: str) -> dict[str, str]:
    output = run_zellij(["--session", session_name, "action", "list-clients"])
    clients: dict[str, str] = {}
    for line in output.splitlines():
        fields = line.split()
        if len(fields) >= 2 and fields[0].isdigit():
            clients[fields[0]] = fields[1]
    return clients


def attach_to_target(session_name: str, tab_id: int | None, pane_id: str | None) -> int:
    existing_clients = _client_panes(session_name)
    if existing_clients:
        raise ValueError("Zellij cannot target a specific client when attaching directly to a tab or pane in a session with attached clients. Attach to the session normally, then select the tab or pane from inside Zellij.")
    with subprocess.Popen(["zellij", "attach", session_name]) as process:
        try:
            while process.poll() is None:
                clients = _client_panes(session_name)
                new_clients = clients.keys() - existing_clients.keys()
                if new_clients:
                    if len(clients) != 1:
                        raise ValueError("Another client attached to the Zellij session before its target could be focused. Attach to the session normally, then select the tab or pane from inside Zellij.")
                    if pane_id is not None and not any(clients[client_id] == pane_id for client_id in new_clients):
                        run_zellij(["--session", session_name, "action", "focus-pane-id", pane_id])
                    elif pane_id is None and tab_id is not None:
                        run_zellij(["--session", session_name, "action", "go-to-tab-by-id", str(tab_id)])
                    break
                time.sleep(0.05)
            return process.wait()
        except (OSError, ValueError):
            process.terminate()
            process.wait()
            raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("session_name")
    parser.add_argument("--tab-id", type=int)
    parser.add_argument("--pane-id")
    arguments = parser.parse_args()
    try:
        exit_code = attach_to_target(session_name=arguments.session_name, tab_id=arguments.tab_id, pane_id=arguments.pane_id)
    except (OSError, ValueError) as error:
        print(f"""Error: {error}""", file=sys.stderr)
        raise SystemExit(1) from error
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
