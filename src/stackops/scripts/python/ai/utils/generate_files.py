#!/usr/bin/env python3
"""Script to generate a markdown table with checkboxes for all Python and shell files in the repo."""

from pathlib import Path
from typing import Annotated, Literal

import typer

from stackops.scripts.python.ai.utils.generate_files_content import generate_content
from stackops.scripts.python.ai.utils.generate_files_utils import (
    filter_files_by_content,
    filter_files_by_name,
    get_python_files,
    get_shell_files,
    resolve_output_base,
    resolve_scan_root,
    split_files_into_chunks,
    validate_split_options,
)


def make_todo_files(
    pattern: Annotated[str, typer.Argument(help="Pattern or keyword to match files by")],
    repo: Annotated[
        str,
        typer.Argument(help="Repository or workspace path. If inside a git repo, its root is used; otherwise the directory itself is scanned."),
    ] = str(Path.cwd()),
    strategy: Annotated[Literal["name", "keywords"], typer.Option("-s", "--strategy", help="Strategy to filter files: 'name' for filename matching, 'keywords' for content matching")] = "name",
    exclude_init: Annotated[bool, typer.Option("-x", "--exclude-init", help="Exclude __init__.py files from the checklist")] = True,
    include_line_count: Annotated[bool, typer.Option("-l", "--line-count", help="Include line count column in the output")] = False,
    output_path: Annotated[str, typer.Option("-o", "--output-path", help="Base path for output files relative to repo root")] = ".ai/todo/files",
    format_type: Annotated[Literal["csv", "md", "txt"], typer.Option("-f", "--format", help="Output format: csv, md (markdown), or txt")] = "md",
    split_every: Annotated[int | None, typer.Option("--split-every", "-e", help="Split output into multiple files, each containing at most this many results")] = None,
    split_to: Annotated[int | None, typer.Option("--split-to", "-t", help="Split output into exactly this many files")] = None,
) -> None:
    """Generate checklist with Python and shell script files in the repository or workspace filtered by pattern."""
    import shutil

    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    try:
        repo_path = resolve_scan_root(Path(repo))
        validate_split_options(split_every=split_every, split_to=split_to)
        output_base = resolve_output_base(repo_root=repo_path, output_path=output_path)
    except ValueError as error:
        console.print(Panel(f"❌ ERROR | {error}", border_style="bold red", expand=False))
        raise typer.Exit(code=1) from error

    todo_dir = repo_path / ".ai" / "todo"
    if todo_dir.exists():
        shutil.rmtree(todo_dir)

    output_base.parent.mkdir(parents=True, exist_ok=True)

    python_files = get_python_files(repo_path, exclude_init=exclude_init)
    shell_files = get_shell_files(repo_path)

    if strategy == "name":
        python_files = filter_files_by_name(python_files, pattern)
        shell_files = filter_files_by_name(shell_files, pattern)
    elif strategy == "keywords":
        python_files = filter_files_by_content(repo_path, python_files, pattern)
        shell_files = filter_files_by_content(repo_path, shell_files, pattern)

    print(f"Scan path: {repo_path}")
    print(f"Strategy: {strategy}")
    print(f"Pattern: {pattern}")
    print(f"Format: {format_type}")
    print(f"Found {len(python_files)} Python files")
    print(f"Found {len(shell_files)} Shell script files")

    all_files = python_files + shell_files
    
    file_chunks = split_files_into_chunks(all_files, split_every, split_to)
    
    extension = {"csv": ".csv", "md": ".md", "txt": ".txt"}[format_type]
    
    output_files = []
    for i, chunk in enumerate(file_chunks):
        chunk_python = [f for f in chunk if f in python_files]
        chunk_shell = [f for f in chunk if f in shell_files]
        
        content = generate_content(chunk_python, chunk_shell, repo_path, format_type, include_line_count)
        
        if len(file_chunks) == 1:
            output_file = output_base.with_suffix(extension)
        else:
            output_file = output_base.parent / f"{output_base.name}_{i+1}{extension}"
        
        output_file.write_text(content)
        output_files.append(output_file)

    console = Console()
    success_msg = f"""✅ SUCCESS | Files generated successfully!
📄 Output files: {', '.join(str(f.relative_to(repo_path)) for f in output_files)}
🐍 Python files: {len(python_files)}
🔧 Shell files: {len(shell_files)}
📊 Total chunks: {len(file_chunks)}"""
    
    console.print(Panel(success_msg, border_style="bold blue", expand=False))


if __name__ == "__main__":
    typer.run(make_todo_files)
