

import argparse
import json

from stackops.scripts.python.graph.cli_graph_shared import (
    DEFAULT_OUTPUT_PATH,
    REPO_ROOT,
)
from stackops.scripts.python.graph.cli_graph_tree import build_cli_graph


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate cli_graph.json from Typer source."
    )
    parser.add_argument(
        "--output",
        "-o",
        type=type(DEFAULT_OUTPUT_PATH),
        default=DEFAULT_OUTPUT_PATH,
        help=f"Output file path (default: {DEFAULT_OUTPUT_PATH.relative_to(REPO_ROOT)})",
    )
    args = parser.parse_args()

    payload = build_cli_graph()
    args.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
