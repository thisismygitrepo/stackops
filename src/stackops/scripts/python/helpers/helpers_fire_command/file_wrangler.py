from pathlib import Path
import platform


def parse_pyfile(file_path: str):
    print(f"🔍 Loading {file_path} ...")
    from typing import NamedTuple

    args_spec = NamedTuple("args_spec", [("name", str), ("type", str), ("default", str | None)])
    func_args: list[list[args_spec]] = [[]]
    import ast

    parsed_ast = ast.parse(Path(file_path).read_text(encoding="utf-8"))
    functions = [node for node in ast.walk(parsed_ast) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    module__doc__ = ast.get_docstring(parsed_ast)
    main_option = f"RUN AS MAIN -- {module__doc__ if module__doc__ is not None else 'NoDocs'}"
    options = [main_option]
    for function in functions:
        if function.name.startswith("__") and function.name.endswith("__"):
            continue
        if any(arg.arg == "self" for arg in function.args.args):
            continue
        doc_string_tmp: str | None = ast.get_docstring(function)
        if doc_string_tmp is None:
            doc_string = "NoDocs"
        else:
            doc_string = doc_string_tmp.replace("\n", " ")
        options.append(f"{function.name} -- {', '.join([arg.arg for arg in function.args.args])} -- {doc_string}")
        tmp = []
        for idx, arg in enumerate(function.args.args):
            if arg.annotation is not None:
                try:
                    type_ = arg.annotation.__dict__["id"]
                except KeyError as ke:
                    type_ = "Any"
                    _ = ke
            else:
                type_ = "Any"
            default_tmp = function.args.defaults[idx] if idx < len(function.args.defaults) else None
            if default_tmp is None:
                default = None
            else:
                if hasattr(default_tmp, "__dict__"):
                    default = default_tmp.__dict__.get("value", None)
                else:
                    default = None
            tmp.append(args_spec(name=arg.arg, type=type_, default=default))
        func_args.append(tmp)
    return options, func_args


def wrap_import_in_try_except(import_line: str, pyfile: str, repo_root: str | None = None) -> None:
    import importlib
    import sys

    module_name = import_line.removeprefix("from ").removesuffix(" import *")

    try:
        module = importlib.import_module(module_name)
        globals().update(module.__dict__)
    except (ImportError, ModuleNotFoundError) as ex:
        print(fr"❌ Failed to import `{pyfile}` as a module: {ex} ")
        print("⚠️ Attempting import with ad-hoc `$PATH` manipulation. DO NOT pickle any objects in this session as correct deserialization cannot be guaranteed.")
        sys.path.append(str(Path(pyfile).parent))
        if repo_root is not None:
            sys.path.append(repo_root)
        fallback_module = importlib.import_module(Path(pyfile).stem)
        globals().update(fallback_module.__dict__)
        print(fr"✅ Successfully imported `{pyfile}`")


def add_to_path(path_variable: str, directory: str) -> str:
    system = platform.system()

    if system == "Windows":
        script = f"""# Check if {path_variable} is defined
if (Test-Path env:{path_variable}) {{
    Write-Host "Adding {directory} to existing {path_variable}"
    $currentValue = [Environment]::GetEnvironmentVariable("{path_variable}", "User")
    $newValue = "$currentValue;{directory}"
    [Environment]::SetEnvironmentVariable("{path_variable}", $newValue, "User")
    $env:{path_variable} = $newValue
}} else {{
    Write-Host "Creating new {path_variable} variable"
    [Environment]::SetEnvironmentVariable("{path_variable}", "{directory}", "User")
    $env:{path_variable} = "{directory}"
}}
Write-Host "{path_variable} is now: $env:{path_variable}\""""
        return script
    script = f"""#!/bin/bash
# Check if {path_variable} is defined and not empty
if [ -z "${{{path_variable}}}" ]; then
    echo "Creating new {path_variable} variable"
    export {path_variable}="{directory}"
else
    echo "Adding {directory} to existing {path_variable}"
    export {path_variable}="${{{path_variable}}}:{directory}"
fi
echo "{path_variable} is now: ${{{path_variable}}}"
"""
    return script
