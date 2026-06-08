# preview

`preview` builds a temporary `uv run` launch context, then opens a selected file or directory in a preview, viewer, or interactive backend such as IPython, Python, Marimo, Jupyter, VS Code, or VisiData.

---

## Usage

```bash
preview [OPTIONS] [PATH]
```

## Arguments

| Argument | Description |
| --- | --- |
| `PATH` | Optional file or directory to inspect before launching the backend |

---

## Options

| Option | Short | Description |
| --- | --- | --- |
| `--project` | `-p` | Reuse a specific `uv` project directory |
| `--uv-with` | `-w` | Add extra packages to the launch environment |
| `--backend` | `-b` | Backend: `ipython`, `python`, `marimo`, `jupyter`, `vscode`, `visidata`, `auto`, `preview`, `browser`, `glow`, or a SQL client |
| `--interactive` | `-i` | Select any available backend interactively |
| `--profile` | `-r` | IPython profile name |
| `--self` | `-s` | Point the project at `~/code/stackops` when that checkout exists |
| `--frozen` | `-f` | Add `--frozen` to the `uv run` invocation |

The backend option also accepts short aliases from the current enum mapping:

- `ipython` or `i`
- `python` or `p`
- `marimo` or `m`
- `jupyter` or `j`
- `vscode` or `c`
- `visidata` or `v`
- `preview`
- `auto`
- `browser` or `b`
- `glow` or `g`
- `rainfrog` or `r`
- `lazysql` or `l`
- `dblab` or `d`
- `usql` or `u`
- `harlequin` or `h`
- `sqlit` or `s`

With `--interactive`, paths expose file-viewer choices by their actual tool names:

- `auto`
- `preview`
- `browser`
- `glow`
- `rainfrog`
- `lazysql`
- `dblab`
- `usql`
- `harlequin`
- `sqlit`

---

## Current launch behavior

`preview` does more than open a shell:

- if `PATH` is a Python file, it stages that file inside a generated temporary script
- if `PATH` is a non-Python file, it generates a reader script using StackOps file readers and prints the parsed content in the chosen backend
- if `PATH` is omitted, it still creates a temporary script and launches the selected backend in the current context

Project resolution is currently:

1. explicit `--project`, if provided
2. nearest `.venv` discovered from the selected file
3. `~/code/stackops`, if that checkout exists and nothing else was selected

---

## Backend-specific notes

- `ipython` is the default backend.
- `python` runs the generated script with plain Python instead of IPython.
- `marimo` converts the generated script to `marimo_nb.py` in a temporary directory, then runs `marimo edit --host 0.0.0.0`.
- `jupyter` emits a temporary `.ipynb` and opens it in JupyterLab.
- `vscode` initializes a temporary `uv` workspace and opens the generated script in VS Code.
- `visidata` opens the selected file directly with `vd`; JSON files use plain `visidata`, other files add `pyarrow`.
- `preview` uses the fullscreen preview flow.
- `auto` uses the file-aware viewer flow.
- `browser` serves browser-viewable files and directories.
- `glow` opens Markdown files in Glow.
- SQL client choices open local DuckDB/SQLite files through the selected database TUI.
- `preview`, `auto`, `browser`, `glow`, and the SQL client backends require `PATH`; calling one of those backends without a path raises an error before launch.

---

## Examples

```bash
# Launch the default IPython backend
preview

# Open a Python file with IPython
preview script.py --backend ipython

# Inspect a data file with VisiData
preview data.csv --backend visidata

# Open Markdown directly in Glow
preview README.md --backend glow

# Open a SQLite file directly in Rainfrog
preview data.sqlite --backend rainfrog

# Open a generated notebook in Marimo
preview analysis.py --backend marimo --project .

# Force the StackOps checkout as the uv project
preview src/stackops/scripts/python/preview.py --self

# Choose a backend interactively
preview data.sqlite --interactive
```

---

## Getting help

```bash
preview --help
```
