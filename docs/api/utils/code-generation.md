# Code Generation and Command Launching

One of the most distinctive parts of `machineconfig` is its ability to turn Python callables into runnable scripts and shell commands. This is what lets higher-level tools generate session tabs, fire remote jobs, or hand off shell commands to another process without writing all the glue by hand.

The key modules are `machineconfig.utils.meta`, `machineconfig.utils.code`, and the installer guard helper in `machineconfig.utils.installer_utils.installer_cli`.

---

## What this layer provides

| API area | Main helpers |
| --- | --- |
| Callable-to-script conversion | `lambda_to_python_script()`, `get_import_module_string()` |
| `uv` command generation | `get_uv_command()`, `get_uv_command_executing_python_file()`, `get_uv_command_executing_python_script()` |
| Script launching | `get_shell_script_running_lambda_function()`, `run_lambda_function()`, `run_shell_script()`, `run_shell_file()` |
| Shell handoff | `exit_then_run_shell_script()` and `exit_then_run_shell_file()` |
| Notebook-style launchers | `run_python_script_in_marimo()` |
| Tool bootstrapping | `install_if_missing(which, binary_name, verbose)` |

---

## From callables to scripts

`lambda_to_python_script()` inspects a no-argument lambda such as:

```python
lambda: build_report(days=7, include_failed=True)
```

and emits Python source for the target callable with the actual argument values baked in. That generated source can then be:

- written to a temporary file
- run with `uv`
- launched inside a session tab
- handed to a remote-execution pipeline

This is the bridge between Python objects and shell-oriented orchestration.

---

## Building execution commands

`machineconfig.utils.code` then handles the shell side:

- normalize the right `uv` executable path for the current platform
- build commands for Python files or inline Python scripts
- generate temporary scripts
- optionally print the generated code before running it
- execute shell snippets in a temporary file and clean them up afterward

### Example

```python
from machineconfig.utils.code import get_shell_script_running_lambda_function
from machineconfig.utils.meta import lambda_to_python_script


def rebuild_index(*, force: bool) -> None:
    print(force)


python_source = lambda_to_python_script(
    lambda: rebuild_index(force=True),
    in_global=True,
    import_module=True,
)

shell_script, py_file = get_shell_script_running_lambda_function(
    lambda: rebuild_index(force=True),
    uv_with=["machineconfig"],
    uv_project_dir=None,
)

print(python_source)
print(shell_script)
print(py_file)
```

---

## Shell handoff and `OP_PROGRAM_PATH`

`exit_then_run_shell_script()` has an important integration behavior:

- if `OP_PROGRAM_PATH` is set to a writable path, it writes the generated script there and exits
- otherwise it falls back to direct execution

That pattern is what lets higher-level tools hand a command off to an external shell runner cleanly instead of always running it in-process.

---

## Bootstrapping required tools

Some workflows need a CLI binary before they can continue. `install_if_missing()` is the lightweight guard for that:

```python
from machineconfig.utils.installer_utils.installer_cli import install_if_missing

install_if_missing(
    which="ipinfo",
    binary_name=None,
    verbose=True,
)
```

It checks for the target binary, optionally prints status, and falls back to the installer pipeline if the tool is missing. For the full installer catalog and curated package groups, see [Jobs and installer APIs](../jobs/index.md).

---

## API reference

## Metaprogramming helpers

::: machineconfig.utils.meta
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Code and shell helpers

::: machineconfig.utils.code
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Installer guard helper

::: machineconfig.utils.installer_utils.installer_cli.install_if_missing
    options:
      show_root_heading: true
      show_source: false
