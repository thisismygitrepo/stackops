import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from stackops.architecture_graph.graph import build_graph_page_payload
from stackops.architecture_graph.renderer import write_html

DEFAULT_DEPTH = 1
DEFAULT_MAX_DEPTH = 3
DEFAULT_OUTPUT_PATH = Path(".ai/architecture_dependencies.html")
DEFAULT_PACKAGE_NAME = "stackops"
DEFAULT_SOURCE_ROOT = Path("src/stackops")


@dataclass(frozen=True, slots=True)
class CliArgs:
    source_root: Path
    package_name: str
    output_path: Path
    depth: int
    max_depth: int


def main() -> None:
    args = parse_cli_args()
    if not args.source_root.exists():
        raise SystemExit(f"source root does not exist: {args.source_root}")
    payload = build_graph_page_payload(
        source_root=args.source_root,
        package_name=args.package_name,
        initial_depth=args.depth,
        max_depth=args.max_depth,
    )
    output_path = write_html(payload=payload, output_path=args.output_path)
    print(f"Wrote {output_path}")


def parse_cli_args() -> CliArgs:
    parser = build_parser()
    namespace = parser.parse_args()
    source_root = cast(Path, getattr(namespace, "source_root"))
    package_name = cast(str, getattr(namespace, "package_name"))
    output_path = cast(Path, getattr(namespace, "output_path"))
    depth = cast(int, getattr(namespace, "depth"))
    max_depth = cast(int, getattr(namespace, "max_depth"))
    if depth < 0:
        raise SystemExit("--depth must be zero or greater")
    if max_depth < depth:
        raise SystemExit("--max-depth must be greater than or equal to --depth")
    return CliArgs(
        source_root=source_root,
        package_name=package_name,
        output_path=output_path,
        depth=depth,
        max_depth=max_depth,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m stackops.architecture_graph",
        description="Generate an interactive HTML dependency graph for StackOps.",
    )
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--package-name", default=DEFAULT_PACKAGE_NAME)
    parser.add_argument("--output", dest="output_path", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--depth", type=int, default=DEFAULT_DEPTH)
    parser.add_argument("--max-depth", type=int, default=DEFAULT_MAX_DEPTH)
    return parser
