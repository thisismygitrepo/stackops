from pathlib import Path


def count_lines(file_path: Path) -> int:
    """Count the number of lines in a file."""
    try:
        return len(file_path.read_text(encoding="utf-8").splitlines())
    except (IOError, UnicodeDecodeError):
        return 0


def generate_csv_content(python_files: list[str], shell_files: list[str], repo_root: Path, include_line_count: bool = False) -> str:
    """Generate CSV content with file information."""
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    if include_line_count:
        writer.writerow(["Type", "Index", "File Path", "Line Count", "Status"])
    else:
        writer.writerow(["Type", "Index", "File Path", "Status"])
    
    for index, file_path in enumerate(python_files, start=1):
        clean_path = file_path.lstrip("./")
        if include_line_count:
            line_count = count_lines(repo_root / file_path)
            writer.writerow(["Python", index, clean_path, line_count, "[ ]"])
        else:
            writer.writerow(["Python", index, clean_path, "[ ]"])
    
    for index, file_path in enumerate(shell_files, start=1):
        clean_path = file_path.lstrip("./")
        if include_line_count:
            line_count = count_lines(repo_root / file_path)
            writer.writerow(["Shell", index, clean_path, line_count, "[ ]"])
        else:
            writer.writerow(["Shell", index, clean_path, "[ ]"])
    
    return output.getvalue()


def generate_txt_content(python_files: list[str], shell_files: list[str]) -> str:
    """Generate plain text content with file paths."""
    all_files = python_files + shell_files
    return "\n".join(file.lstrip("./") for file in all_files)


def generate_markdown_table(python_files: list[str], shell_files: list[str], repo_root: Path, include_line_count: bool = False) -> str:
    """Generate markdown table with checkboxes."""
    header = "# File Checklist\n\n"

    content = ""

    if python_files:
        content += "## Python Files\n\n"
        if include_line_count:
            python_with_counts = [(file, count_lines(repo_root / file)) for file in python_files]
            python_with_counts.sort(key=lambda x: x[1], reverse=True)
            python_files = [file for file, _ in python_with_counts]
            
            content += "| Index | File Path | Line Count | Status |\n|-------|-----------|------------|--------|\n"
        else:
            content += "| Index | File Path | Status |\n|-------|-----------|--------|\n"
        for index, file_path in enumerate(python_files, start=1):
            clean_path = file_path.lstrip("./")
            if include_line_count:
                line_count = count_lines(repo_root / file_path)
                content += f"| {index} | {clean_path} | {line_count} | - [ ] |\n"
            else:
                content += f"| {index} | {clean_path} | - [ ] |\n"

    if shell_files:
        content += "\n## Shell Script Files\n\n"
        if include_line_count:
            shell_with_counts = [(file, count_lines(repo_root / file)) for file in shell_files]
            shell_with_counts.sort(key=lambda x: x[1], reverse=True)
            shell_files = [file for file, _ in shell_with_counts]
            
            content += "| Index | File Path | Line Count | Status |\n|-------|-----------|------------|--------|\n"
        else:
            content += "| Index | File Path | Status |\n|-------|-----------|--------|\n"
        for index, file_path in enumerate(shell_files, start=1):
            clean_path = file_path.lstrip("./")
            if include_line_count:
                line_count = count_lines(repo_root / file_path)
                content += f"| {index} | {clean_path} | {line_count} | - [ ] |\n"
            else:
                content += f"| {index} | {clean_path} | - [ ] |\n"

    return header + content


def generate_content(python_files: list[str], shell_files: list[str], repo_root: Path, 
                    format_type: str, include_line_count: bool) -> str:
    """Generate content based on format type."""
    if format_type == "csv":
        return generate_csv_content(python_files, shell_files, repo_root, include_line_count)
    elif format_type == "md":
        return generate_markdown_table(python_files, shell_files, repo_root, include_line_count)
    elif format_type == "txt":
        return generate_txt_content(python_files, shell_files)
    else:
        raise ValueError(f"Unsupported format: {format_type}")
