# StackOps Command Reference: `utils file`

Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on 2026-06-21.

This page expands exactly one level below `utils file`. Follow child links one command segment at a time.

## Current Command

- Path: `utils file`
- Kind: `group`
- Source: `src/stackops/scripts/python/utils.py` -> `stackops.scripts.python.helpers.helpers_utils.file_utils_app.get_app` via `file`
- Help: `📁 <f> File, document, and database utilities`

## Help Commands

- `UV_CACHE_DIR=/tmp/uv-cache uv run utils file --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run stackops utils file --help`

## Immediate Children

- [`utils file edit`](command--utils--file--edit.md) - command with no child commands. Help: `✏ <e> Open a file in the default editor.`.
- [`utils file download`](command--utils--file--download.md) - command with no child commands. Help: `↓ <d> Download a file from a URL and optionally decompress it.`.
- [`utils file scrape`](command--utils--file--scrape.md) - command with no child commands. Help: `<s> Scrape a page to Markdown with Scrapling.`.
- [`utils file pdf-merge`](command--utils--file--pdf-merge.md) - command with no child commands. Help: `◫ <p> Merge PDF files into one.`.
- [`utils file pdf-compress`](command--utils--file--pdf-compress.md) - command with no child commands. Help: `↧ <c> Compress a PDF file.`.
- [`utils file ocr`](command--utils--file--ocr.md) - command with no child commands. Help: `☀ <o> OCR, layout, detection, and table recognition with Surya.`.
- [`utils file read-db`](command--utils--file--read-db.md) - command with no child commands. Help: `🗃 <r> TUI DB Visualizer.`.

## Notes

- Developer-only command groups under `devops self` depend on the developer checkout at `~/code/stackops`.
- Callback groups are invoked as the group command itself when their command reference has no children.
- The generated graph stores aliases on each node. Use `src/stackops/scripts/python/graph/cli_graph.json` when alias details matter.
- Docs may lag source. Prefer command paths and behavior verified from current Typer source and `--help` output.
