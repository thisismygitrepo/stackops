"""Static CLI signature policy enforced at graph build time."""

from typing import Any

CANONICAL_SHORTS: dict[str, str] = {
    "--all": "-a",
    "--apps": "-a",
    "--cloud": "-c",
    "--command": "-c",
    "--configs": "-c",
    "--directory": "-d",
    "--dotfiles": "-d",
    "--editor": "-e",
    "--host": "-H",
    "--interactive": "-i",
    "--json": "-j",
    "--kill-all": "-k",
    "--local": "-l",
    "--max-files": "-m",
    "--on-conflict": "-c",
    "--output-dir": "-o",
    "--output-path": "-o",
    "--overwrite": "-o",
    "--package-spec": "-p",
    "--password": "-p",
    "--pull": "-p",
    "--raw": "-r",
    "--record": "-r",
    "--rel2home": "-r",
    "--remote": "-r",
    "--root": "-R",
    "--run": "-R",
    "--scope": "-s",
    "--self": "-s",
    "--source": "-s",
    "--ssh": "-s",
    "--symlinks": "-l",
    "--test-layout": "-L",
    "--tools": "-t",
    "--totp": "-t",
    "--transfers": "-T",
    "--zip": "-z",
}

SHORT_OVERRIDES: dict[tuple[str, str], str] = {
    ("devops repos guard", "--cloud"): "-C",
    ("devops repos action", "--command"): "-C",
    ("devops repos action", "--pull"): "-P",
    ("devops config sync", "--source"): "-S",
    ("devops config secrets search", "--scope"): "-S",
    ("agents add-mcp", "--source"): "-S",
    ("agents parallel run-parallel", "--source"): "-S",
    ("devops network share-terminal", "--password"): "-w",
    ("devops network share-server", "--password"): "-w",
    ("utils file download", "--output-dir"): "-O",
    ("utils pyproject check-deps", "--output-path"): "-O",
    ("utils file ocr", "--package-spec"): "-P",
    ("fire", "--remote"): "-R",
    ("devops config terminal tmux-style set-option", "--raw"): "-R",
    ("devops self status", "--ssh"): "-h",
    ("terminal export", "--overwrite"): "-w",
}

REQUIRED_OPTION_ALLOWLIST: set[tuple[str, str]] = {
    ("devops repos version declare", "--message"),
    ("devops network cloudflare sync-cloudflare-routes", "--hostname"),
    ("devops network cloudflare add-ip-exclusion-to-warp", "--ip"),
    ("terminal balance-load", "--max-threshold"),
    ("terminal run-all", "--max-parallel-tabs"),
    ("terminal create-from-function", "--num-process"),
}


def _iter_commands(node: dict[str, Any]) -> list[dict[str, Any]]:
    commands: list[dict[str, Any]] = []
    if node.get("kind") == "command":
        commands.append(node)
    kids = node.get("children")
    if isinstance(kids, dict):
        kids = list(kids.values())
    elif kids is None:
        kids = []
    for child in kids:
        commands.extend(_iter_commands(child))
    return commands


def _option_decls(param: dict[str, Any]) -> tuple[list[str], list[str]]:
    decls: list[str] = param.get("typer", {}).get("param_decls", [])
    longs = [d for d in decls if d.startswith("--")]
    shorts = [d for d in decls if d.startswith("-") and not d.startswith("--")]
    return longs, shorts


def validate_cli_graph(payload: dict[str, Any]) -> None:
    violations: list[str] = []
    for node in _iter_commands(payload["root"]):
        path: str = node["fullPath"]
        seen_shorts: dict[str, str] = {}
        seen_longs: dict[str, str] = {}
        for param in node.get("signature", {}).get("parameters", []):
            typer_meta: dict[str, Any] = param.get("typer", {})
            if typer_meta.get("kind") != "option":
                continue
            longs, shorts = _option_decls(param)
            primary_long = longs[0].split("/")[0] if longs else ""
            has_secondary = any("/" in d for d in longs + shorts)
            name: str = param["name"]

            if param.get("type") == "bool" and not has_secondary and param.get("default") is True:
                violations.append(f"{path}: {name} bool flag {primary_long or name} defaults True without a --x/--no-x pair (inert flag)")

            if param.get("required") and (path, primary_long) not in REQUIRED_OPTION_ALLOWLIST:
                violations.append(f"{path}: {name} required option {primary_long}; primary operands must be positional arguments")

            if primary_long in CANONICAL_SHORTS:
                expected = SHORT_OVERRIDES.get((path, primary_long), CANONICAL_SHORTS[primary_long])
                actual = shorts[0].split("/")[0] if shorts else ""
                if actual != expected:
                    violations.append(f"{path}: {primary_long} short is {actual or 'missing'}, canonical is {expected}")

            for long_flag in longs:
                for part in long_flag.split("/"):
                    if part in seen_longs and seen_longs[part] != name:
                        violations.append(f"{path}: long flag {part} declared by both {seen_longs[part]} and {name}")
                    seen_longs[part] = name
            for short in shorts:
                for part in short.split("/"):
                    if part in seen_shorts and seen_shorts[part] != name:
                        violations.append(f"{path}: short flag {part} declared by both {seen_shorts[part]} and {name}")
                    seen_shorts[part] = name
    if violations:
        raise ValueError("CLI signature policy violations:\n  " + "\n  ".join(violations))
