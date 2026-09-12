import argparse
import sys
from pathlib import Path
from typing import cast

from stackops.utils.dashboards.constants import DASHBOARD_STATE_DIR
from stackops.utils.dashboards.lifecycle import run_dashboard


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch or reuse an owned Streamlit dashboard.")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("script", type=Path)
    args = parser.parse_args()
    port = cast(int, args.port)
    script = cast(Path, args.script).resolve(strict=True)
    command = (
        sys.executable, "-m", "streamlit", "run", "--server.address", "0.0.0.0",
        "--server.headless", "true", "--server.port", str(port), str(script),
    )
    try:
        return run_dashboard(
            command=command, port=port, identity=f"""Streamlit {script.name}""", cwd=Path.cwd(),
            environment={}, health_path="/_stcore/health", state_dir=DASHBOARD_STATE_DIR,
        )
    except (OSError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
