# croshell

`croshell` launches a file or project context inside an interactive backend such as IPython, Python, Marimo, Jupyter, VS Code, or VisiData.

---

## Usage

```bash
croshell [OPTIONS] [PATH]
```

---

## Arguments

| Argument | Description |
|----------|-------------|
| `PATH` | Optional file or directory to open before launching the backend |

---

## Options

| Option | Short | Description |
|--------|-------|-------------|
| `--project` | `-p` | Use a specific `uv` project directory |
| `--uv-with` | `-w` | Add extra packages to the launched `uv` environment |
| `--backend` | `-b` | Choose the backend: `ipython` (default), `python`, `marimo`, `jupyter`, `vscode`, or `visidata` |
| `--profile` | `-r` | IPython profile name when using the IPython backend |
| `--self` | `-s` | Use the local `~/code/machineconfig` checkout as the project |
| `--frozen` | `-f` | Freeze the environment so `uv` does not change installed packages |

---

## Typical flows

```bash
# Open the current project in the default IPython backend
croshell

# Open a Python file in IPython
croshell script.py --backend ipython

# Inspect a data file in VisiData
croshell data.csv --backend visidata

# Launch the selected file through Marimo
croshell notebook.py --backend marimo --project .

# Reuse the machineconfig checkout as the active project
croshell src/machineconfig/scripts/python/croshell.py --self
```

---

## Notes

- `ipython` is the default backend when you do not pass `--backend`.
- When `PATH` points to a non-Python file, `croshell` builds a small reader script and launches the selected backend against that generated context.
- Use `--project` when you want `croshell` to reuse a specific local `uv` project instead of creating an ad-hoc environment.
- Use live help to confirm the exact backend and option surface in your installed version:

```bash
croshell --help
```
