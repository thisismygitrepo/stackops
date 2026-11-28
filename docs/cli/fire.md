# fire

`fire` resolves a file, directory, or partial script name, then builds an execution command around Python Fire, plain Python, IPython, Streamlit, Jupyter, Marimo, shell sourcing, or direct executable launch.

---

## Usage

```bash
fire [OPTIONS] COMMAND [ARGS]...
```

| Command | Usage | Purpose |
| --- | --- | --- |
| `run` | `fire run [OPTIONS] [PATH] [FUNCTION]` | Run a script or Python function |
| `streamlit` | `fire streamlit [OPTIONS] [PATH]` | Launch a Streamlit app |
| `jupyter` | `fire jupyter [OPTIONS] [PATH]` | Open a file in JupyterLab |
| `marimo` | `fire marimo [OPTIONS] [PATH]` | Edit a Marimo notebook |

The commands also have hidden one-letter aliases: `r`, `s`, `j`, and `m`. `fire` without a command prints help; a bare `fire script.py` is rejected.

`fire --non-interactive`/`-N` (or `STACKOPS_NON_INTERACTIVE`) never prompts or opens a picker; it is enabled automatically without a terminal.

## Arguments

| Argument | Description |
| --- | --- |
| `PATH` | Path to the file to run, or a directory / partial name that can be resolved interactively. Defaults to the current directory. |
| `FUNCTION` | Optional Python function name (`run` only) |

---

## Current execution flags

| Command | Flags |
| --- | --- |
| `run` | `--frozen` (`-F`), `--cmd` (`-B`), `--interactive` (`-i`), `--debug` (`-d`), `--choose-function` (`-c`), `--loop` (`-l`), `--module` (`-m`), `--script` (`-s`), `--optimized` (`-O`), `--jit` (`-J`), `--root-repo` (`-r`), `--path-export` (`-P`), `--git-pull` (`-g`), `--watch` (`-w`) |
| `streamlit` | `--frozen` (`-F`), `--jit` (`-J`), `--root-repo` (`-r`), `--hold-directory` (`-D`), `--path-export` (`-P`), `--git-pull` (`-g`), `--watch` (`-w`) |
| `jupyter` | `--frozen` (`-F`), `--jit` (`-J`), `--root-repo` (`-r`), `--path-export` (`-P`), `--git-pull` (`-g`), `--watch` (`-w`) |
| `marimo` | `--frozen` (`-F`), `--jit` (`-J`), `--root-repo` (`-r`) |

---

## Passing function arguments

`fire run` keeps extra Fire arguments in the pass-through segment after `--`.

Use this form:

```bash
fire run jobs.py run -- --limit=2 --dry-run
```

Not this:

```bash
fire run jobs.py run --limit=2
```

That extra `--` matters because the wrapper parses its own options first, then forwards the remaining raw arguments into the generated Python Fire command.

---

## Current path resolution

`fire` does not require an exact filename up front.

- if `PATH` is a file, it uses it directly
- if `PATH` is a directory, it recursively scans for candidate scripts and asks you to choose
- if `PATH` does not exist, it searches for a matching filename or partial path
- `--root-repo` changes that search root to the git repository root of the current working directory

Supported target types in the current route:

| Target | Behavior |
| --- | --- |
| `.py` | Build a Python, IPython, Streamlit, Jupyter, or Marimo command |
| `.sh` / `.ps1` | Source the script |
| no suffix | Execute directly |

`fire streamlit` and `fire marimo` require a `.py` file; `fire jupyter` accepts `.py` or `.ipynb`.

Python-backed commands run through `uv run --no-sync` against the project that owns the file: the nearest `pyproject.toml` up to the repository root, with its `.venv`. That environment must already exist; prepare it with `uv sync`. A file outside any project runs with `--no-project`.

---

## Function selection

`fire run --choose-function` behaves differently by file type:

- for Python files, it lists the file's functions (dunder functions and methods taking `self` are skipped) and offers a `RUN AS MAIN` option
- for `.sh` files, it offers non-comment, non-empty, non-`echo` lines and writes the selected lines into a temporary script

For Python files, when you choose a function and did not already pass kwargs, the helper prompts for argument values based on the parsed signature.

Examples:

```bash
fire run tools.py -c
fire run tools.py cleanup -- --days=30
```

---

## Notebook and app modes

`fire marimo`:

- checks whether the selected file is already a valid marimo notebook
- if not, converts it into a temporary notebook under `~/tmp_results/tmp_scripts/marimo/...`
- launches `marimo edit --host 0.0.0.0`

`fire streamlit`:

- reads `.streamlit/config.toml` beside the file, or from the parent app directory when the file lives under `pages/`
- uses the configured port when present, otherwise `8501`
- prints the LAN / hostname / localhost URLs
- launches `streamlit run --server.address 0.0.0.0 --server.headless true` from the app's directory; `--hold-directory` keeps the current directory instead

`fire jupyter` opens the selected `.py` or `.ipynb` file in JupyterLab.

Examples:

```bash
fire streamlit dashboard.py
fire marimo notebook.py
fire jupyter analysis.py
```

---

## Interactive and development helpers

- `--interactive` launches IPython with the default profile.
- `--debug` runs the file under `pudb` on Linux and macOS, or `ipdb` on Windows.
- `--jit` (`-J`) sets `PYTHON_JIT=1` before launching the Python-backed command. This opts into CPython's experimental JIT when the selected interpreter supports it.
- `--watch` prefixes the final command with `watchexec --restart --exts py,sh,ps1` (`py,ipynb` for `fire jupyter`).
- `--frozen/-F` passes `--frozen` to `uv run`, using the existing lockfile without updating it. File watching remains controlled by `--watch`.
- `--git-pull` runs `git -C <script-dir> pull` first.
- `--path-export` prepends a shell snippet that appends the repo root to `PYTHONPATH`.
- `--loop` wraps the command in a loop with a half-second pause between runs. On Linux and macOS, `Ctrl+C` during a run starts the next one; `Ctrl+C` during the pause ends the loop. On Windows, `Ctrl+C` ends the loop.

Examples:

```bash
fire run src/app.py serve -- --host=0.0.0.0 --port=8000
fire run src/app.py -i
fire run src/app.py -w -g
fire run nested/tool.py -r -P
```

---

## Notes

- `stackops fire` and standalone `fire` expose the same commands and options, including `--frozen/-F`.

---

## Getting help

```bash
fire --help
fire run --help
fire streamlit --help
fire jupyter --help
fire marimo --help
```
