"""Pure Python implementation for seek command without Typer."""

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from machineconfig.scripts.python.helpers.helpers_search.ast_search import SymbolInfo


def seek(
    path: str,
    search_term: str,
    ast: bool,
    symantic: bool,
    extension: str | None,
    file: bool,
    dotfiles: bool,
    rga: bool,
    edit: bool,
    install_dependencies: bool,
) -> None:
    """seek across files, text matches, and code symbols."""

    if install_dependencies:
        _install_dependencies()
        return
    if symantic:
        _ = extension
        _run_symantic_search(path=path, query=search_term, extension=extension)
        return
    if ast:
        _run_ast_search(path=path)
        return
    if file:
        _run_file_search(directory=path, dotfiles=dotfiles, edit=edit, search_term=search_term)
        return

    from pathlib import Path
    import sys
    import tempfile
    import io

    is_temp_file = False
    if not sys.stdin.isatty() and Path(path).is_dir():
        # Use UTF-8 encoding to handle emoji and Unicode characters on Windows
        if sys.stdin.encoding != "utf-8":
            stdin_wrapper = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace")
            content = stdin_wrapper.read()
        else:
            content = sys.stdin.read()
        if content:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False, prefix="seek_stdin_") as temp_file:
                temp_file.write(content)
                path = temp_file.name
            is_temp_file = True

    if Path(path).absolute().resolve().is_file():
        from machineconfig.utils.code import exit_then_run_shell_script

        code = search_file_with_context(path=path, is_temp_file=is_temp_file, edit=edit)
        exit_then_run_shell_script(script=code, strict=False)
        return

    _run_text_search(rga=rga, directory=path, search_term=search_term)


def _install_dependencies() -> None:
    """Install required dependencies."""
    from machineconfig.utils.installer_utils.installer_cli import install_if_missing

    install_if_missing(which="fzf", binary_name=None, verbose=True)
    install_if_missing(which="tv", binary_name=None, verbose=True)
    install_if_missing(which="bat", binary_name=None, verbose=True)
    install_if_missing(which="fd", binary_name=None, verbose=True)
    install_if_missing(which="rg", binary_name=None, verbose=True)
    install_if_missing(which="rga", binary_name=None, verbose=True)


def search_file_with_context(path: str, is_temp_file: bool, edit: bool) -> str:
    import platform
    import base64
    from pathlib import Path

    abs_path = str(Path(path).absolute())
    if platform.system() in {"Linux", "Darwin"}:
        if edit:
            code = """
res=$(nl -ba -w1 -s' ' "$TEMP_FILE" | tv \
--preview-command "bat --color=always --style=numbers --highlight-line {split: :0} $TEMP_FILE" \
--preview-size 80 \
--preview-offset "{split: :0}" \
--source-output "{}")
if [ -n "$res" ]; then
    line=$(echo "$res" | cut -d' ' -f1)
    hx "$TEMP_FILE:$line"
fi
"""
        else:
            code = """
nl -ba -w1 -s' ' "$TEMP_FILE" | tv \
--preview-command "bat --color=always --style=numbers --highlight-line {split: :0} $TEMP_FILE" \
--preview-size 80 \
--preview-offset "{split: :0}" \
--source-output "{}" \
| cut -d' ' -f2-
"""
        code = code.replace("$TEMP_FILE", abs_path)
        if is_temp_file:
            code += f"\nrm {path}"
    elif platform.system() == "Windows":
        # Windows: avoid piping INTO `tv` (it breaks TUI interactivity on Windows terminals).
        # Use `tv --source-command` so stdin remains attached to the console.
        # Note: using `cmd /C type` here has proven brittle due to quoting/command-line parsing
        # differences; generate the numbered lines via a self-contained PowerShell command.
        abs_path_escaped = abs_path.replace("'", "''")
        # Use `-EncodedCommand` to avoid nested quoting issues across PowerShell/tv/cmd.
        ps_script = (
            "$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new(); "
            "$i = 0; "
            f"Get-Content -LiteralPath '{abs_path_escaped}' | ForEach-Object {{ $i = $i + 1; \"{{0}} {{1}}\" -f $i, $_ }}"
        )
        encoded = base64.b64encode(ps_script.encode("utf-16le")).decode("ascii")
        source_cmd = f"powershell -NoProfile -ExecutionPolicy Bypass -EncodedCommand {encoded}"
        source_cmd_ps_literal = source_cmd.replace("'", "''")
        if edit:
            code = f"""
$sourceCmd = '{source_cmd_ps_literal}'
$res = tv `
--source-command $sourceCmd `
--preview-command 'bat --color=always --style=numbers --highlight-line {{split: :0}} "{abs_path}"' `
--preview-size 80 `
--preview-offset "{{split: :0}}" `
--source-output "{{}}"
if ($res) {{
    $line = $res.Split(' ')[0]
    hx "{abs_path_escaped}:$line"
}}
"""
        else:
            code = f"""
$sourceCmd = '{source_cmd_ps_literal}'
tv `
--source-command $sourceCmd `
--preview-command 'bat --color=always --style=numbers --highlight-line {{split: :0}} "{abs_path}"' `
--preview-size 80 `
--preview-offset "{{split: :0}}" `
--source-output "{{}}" | ForEach-Object {{ $_ -replace '^\\d+\\s+', '' }}
"""
        if is_temp_file:
            code += f"\nRemove-Item '{abs_path_escaped}' -Force"
    else:
        raise RuntimeError(f"Unsupported platform, {platform.system()}")
    return code


def _run_symantic_search(path: str, query: str, extension: str | None) -> None:
    """Run symantic search."""
    if query == "":
        # print("❓ No search term provided for symantic search.")
        # return
        query = input("Enter search term for symantic search: ")

    from pathlib import Path

    path_obj = Path(path).absolute()
    if path_obj.is_file():
        text_files = [str(path_obj)]
    else:
        if extension is not None:
            # Find files with the given extension
            text_files = list(map(str, path_obj.rglob(f"*{extension}")))
        else:
            import subprocess

            def get_text_files(root: str) -> list[str]:
                result = subprocess.run(["rg", "--files", "-0", root], stdout=subprocess.PIPE, check=True)
                return result.stdout.decode().split("\0")[:-1]

            text_files = get_text_files(str(path_obj))

    from typing import TypedDict

    class SymanticSearchResult(TypedDict):
        filename: str
        start_line_number: int
        end_line_number: int
        match_line_number: int
        distance: float
        content: str

    def symantic_search(query: str, text_files: list[str]) -> list[SymanticSearchResult]:
        # semtools search "hi" ./devcontainer.json --json
        import random

        random_suffix = str(random.randint(1000, 9999))
        import string

        random_suffix += "".join(random.choices(string.ascii_letters + string.digits, k=8))
        results_file = Path.home().joinpath("tmp_results", "tmp_text", "symantic_search", "results_" + random_suffix + ".json")
        results_file.parent.mkdir(parents=True, exist_ok=True)
        command = f"""semtools search "{query}" {" ".join(text_files)} --json --top-k 5 --n-lines 10 > {results_file}"""
        import subprocess

        subprocess.run(command, shell=True, check=True)
        import json

        with open(results_file, "r", encoding="utf-8") as f:
            results_json = f.read()
        results: list[SymanticSearchResult] = json.loads(results_json)["results"]
        return results

    if len(text_files) > 50:
        print(
            f"⚠️ Found {len(text_files)} text files, which may take a while to search through symantically. Consider providing a more specific path or file extension filter."
        )
        return None
    results = symantic_search(query=query, text_files=text_files)

    results_as_dict = {
        res["content"]: res["content"]
        + f"\n\nDetails:\n{res['filename']}:{res['start_line_number']}-{res['end_line_number']}\nMatch: {res['match_line_number']}\nDistance: {res['distance']}"
        for res in results
    }
    from machineconfig.utils.options_utils.tv_options import choose_from_dict_with_preview

    preview_extension = Path(text_files[0]).suffix
    choose_from_dict_with_preview(options_to_preview_mapping=results_as_dict, extension=preview_extension, multi=False, preview_size_percent=75.0)


def _run_ast_search(path: str) -> None:
    """Run AST search."""
    from machineconfig.scripts.python.helpers.helpers_search.ast_search import get_repo_symbols
    from machineconfig.utils.options_utils.tv_options import choose_from_dict_with_preview

    symbols = get_repo_symbols(path)
    options_to_preview_mapping, symbol_lookup = _build_ast_option_lookup(symbols=symbols)

    if len(symbols) == 0:
        print("❓ No symbols found in the repository.")
        return
    try:
        selected_key = choose_from_dict_with_preview(
            options_to_preview_mapping=options_to_preview_mapping, extension="py", multi=False, preview_size_percent=75.0
        )
        if selected_key is None:
            print("❓ Selection cancelled.")
            return
        selected_symbol = symbol_lookup.get(selected_key)
        if selected_symbol is None:
            print("❌ Selected symbol could not be resolved.")
            return
        from rich import print_json
        import json

        selected_symbol_json = json.dumps(_build_ast_output_payload(symbol=selected_symbol), indent=4)
        print_json(selected_symbol_json)
    except Exception as e:
        print(f"❌ Error during selection: {e}")


def _build_ast_option_lookup(symbols: list["SymbolInfo"]) -> tuple[dict[str, str], dict[str, "SymbolInfo"]]:
    options_to_preview_mapping: dict[str, str] = {}
    symbol_lookup: dict[str, "SymbolInfo"] = {}
    for symbol in symbols:
        option_key = _build_ast_option_key(symbol=symbol)
        options_to_preview_mapping[option_key] = _build_ast_option_preview(symbol=symbol)
        symbol_lookup[option_key] = symbol
    return options_to_preview_mapping, symbol_lookup


def _build_ast_option_key(symbol: "SymbolInfo") -> str:
    return f"""{symbol["path"]}    [{symbol["file_path"]}:{symbol["line"]}]"""


def _build_ast_option_preview(symbol: "SymbolInfo") -> str:
    header = f"""# {symbol["type"]}: {symbol["path"]}
# {symbol["file_path"]}:{symbol["line"]}-{symbol["end_line"]}"""
    if symbol["body"] == "":
        return header
    return f"""{header}

{symbol["body"]}"""


def _build_ast_output_payload(symbol: "SymbolInfo") -> dict[str, str | int]:
    return {
        "type": symbol["type"],
        "name": symbol["name"],
        "path": symbol["path"],
        "file_path": symbol["file_path"],
        "line": symbol["line"],
        "end_line": symbol["end_line"],
        "docstring": symbol["docstring"],
    }


def _run_file_search(directory: str | None, dotfiles: bool, edit: bool, search_term: str) -> None:
    """Run file search."""
    import platform

    platform_name = platform.system()
    query_argument = _get_fzf_query_argument(search_term=search_term, platform_name=platform_name)
    source_command = _get_file_search_source_command(dotfiles=dotfiles)

    if not edit:
        script = """fzf --ansi --preview-window 'right:60%' --preview 'bat --color=always --style=numbers,grid,header --line-range :300 {}' {QUERY_ARGUMENT}"""
        if source_command != "":
            script = source_command + script
        script = script.replace("{QUERY_ARGUMENT}", query_argument)
        script = _prepend_directory_change(script=script, directory=directory, platform_name=platform_name)
        from machineconfig.utils.code import run_shell_script

        run_shell_script(script=script, display_script=True, clean_env=False)
        return

    if platform_name in {"Linux", "Darwin"}:
        script = """
selected=$({SOURCE_CMD} fzf --ansi --preview-window 'right:60%' --preview 'bat --color=always --style=numbers,grid,header --line-range :300 {}' {QUERY_ARGUMENT})
if [ -n "$selected" ]; then
    res=$(nl -ba -w1 -s' ' "$selected" | tv \
    --preview-command "bat --color=always --style=numbers --highlight-line {split: :0} $selected" \
    --preview-size 80 \
    --preview-offset "{split: :0}" \
    --source-output "{}")
    if [ -n "$res" ]; then
        line=$(echo "$res" | cut -d' ' -f1)
        hx "$selected:$line"
    fi
fi
"""
        script = script.replace("{SOURCE_CMD}", source_command)
        script = script.replace("{QUERY_ARGUMENT}", query_argument)
    elif platform_name == "Windows":
        script = r"""
$selected = {SOURCE_CMD} fzf --ansi --preview-window 'right:60%' --preview 'bat --color=always --style=numbers,grid,header --line-range :300 {}' {QUERY_ARGUMENT}
if ($selected) {
    $choicesPath = Join-Path $env:TEMP ("seek_choices_" + [guid]::NewGuid().ToString() + ".txt")
    $i = 0
    Get-Content -LiteralPath "$selected" | ForEach-Object { $i = $i + 1; "{0} {1}" -f $i, $_ } | Set-Content -LiteralPath $choicesPath -Encoding utf8
    $sourceCmd = 'cmd /C type "' + $choicesPath + '"'
    $previewCmd = 'bat --color=always --style=numbers --highlight-line {split: :0} "' + $selected + '"'
    $res = tv `
    --source-command $sourceCmd `
    --preview-command $previewCmd `
    --preview-size 80 `
    --preview-offset "{split: :0}" `
    --source-output "{}"
    Remove-Item -LiteralPath $choicesPath -Force -ErrorAction SilentlyContinue
    if ($res) {
        $line = $res.Split(' ')[0]
        hx "$($selected):$line"
    }
}
"""
        script = script.replace("{SOURCE_CMD}", source_command)
        script = script.replace("{QUERY_ARGUMENT}", query_argument)
    else:
        raise RuntimeError("Unsupported platform")

    script = _prepend_directory_change(script=script, directory=directory, platform_name=platform_name)
    from machineconfig.utils.code import run_shell_script

    run_shell_script(script=script, display_script=True, clean_env=False)


def _get_file_search_source_command(dotfiles: bool) -> str:
    """Return the shell source used for file search candidates."""
    if dotfiles:
        return ""
    return "fd --type file | "


def _run_text_search(rga: bool, directory: str | None, search_term: str) -> None:
    """Run text search using fzf with ripgrep."""
    import platform

    import machineconfig.scripts.python.helpers.helpers_seek.scripts_linux as linux_scripts
    import machineconfig.scripts.python.helpers.helpers_seek.scripts_macos as macos_scripts
    import machineconfig.scripts.python.helpers.helpers_seek.scripts_windows as windows_scripts

    from machineconfig.scripts.python.helpers.helpers_seek.scripts_linux import FZFG_PATH_REFERENCE as LINUX_FZFG_PATH_REFERENCE
    from machineconfig.scripts.python.helpers.helpers_seek.scripts_macos import FZFG_PATH_REFERENCE as MACOS_FZFG_PATH_REFERENCE
    from machineconfig.scripts.python.helpers.helpers_seek.scripts_windows import FZFG_PATH_REFERENCE as WINDOWS_FZFG_PATH_REFERENCE
    from machineconfig.utils.path_reference import get_path_reference_path
    platform_name = platform.system()

    if platform_name == "Linux":
        script = get_path_reference_path(module=linux_scripts, path_reference=LINUX_FZFG_PATH_REFERENCE).read_text(
            encoding="utf-8"
        )
    elif platform_name == "Windows":
        script = get_path_reference_path(module=windows_scripts, path_reference=WINDOWS_FZFG_PATH_REFERENCE).read_text(
            encoding="utf-8"
        )
    elif platform_name == "Darwin":
        script = get_path_reference_path(module=macos_scripts, path_reference=MACOS_FZFG_PATH_REFERENCE).read_text(
            encoding="utf-8"
        )
    else:
        raise RuntimeError("Unsupported platform")
    if rga:
        script = script.replace("rg ", "rga ").replace("ripgrep", "ripgrep-all")
    script = _set_initial_query(script=script, search_term=search_term, platform_name=platform_name)
    script = _prepend_directory_change(script=script, directory=directory, platform_name=platform_name)
    from machineconfig.utils.code import exit_then_run_shell_script

    exit_then_run_shell_script(script=script, strict=False)


def _prepend_directory_change(script: str, directory: str | None, platform_name: str) -> str:
    """Prefix a working-directory change command using platform-appropriate quoting."""
    if directory is None or directory == "":
        return script
    if platform_name == "Windows":
        return f"Set-Location -LiteralPath {_to_powershell_single_quoted(directory)}\n{script}"
    if platform_name in {"Linux", "Darwin"}:
        return f"cd {_to_shell_quoted(directory)}\n{script}"
    raise RuntimeError(f"Unsupported platform: {platform_name}")


def _set_initial_query(script: str, search_term: str, platform_name: str) -> str:
    """Inject the initial search term into a platform-specific search script."""
    if platform_name == "Windows":
        return script.replace("$initialQuery = ''", f"$initialQuery = {_to_powershell_single_quoted(search_term)}", 1)
    if platform_name in {"Linux", "Darwin"}:
        return script.replace('INITIAL_QUERY=""', f"INITIAL_QUERY={_to_shell_quoted(search_term)}", 1)
    raise RuntimeError(f"Unsupported platform: {platform_name}")


def _to_shell_quoted(value: str) -> str:
    """Return a bash-safe single argument literal."""
    import shlex

    return shlex.quote(value)


def _to_powershell_single_quoted(value: str) -> str:
    """Return a PowerShell single-quoted string literal."""
    return "'" + value.replace("'", "''") + "'"


def _get_fzf_query_argument(search_term: str, platform_name: str) -> str:
    """Build a platform-appropriate --query argument for fzf."""
    if search_term == "":
        return ""
    if platform_name == "Windows":
        return f"--query {_to_powershell_single_quoted(search_term)}"
    if platform_name in {"Linux", "Darwin"}:
        return f"--query {_to_shell_quoted(search_term)}"
    raise RuntimeError(f"Unsupported platform: {platform_name}")
