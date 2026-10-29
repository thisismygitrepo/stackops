# seek

`seek` is the interactive search entrypoint for file lists, text matches, file previews, AST symbols, and semantic (meaning-based) search over text chunks.

---

## Usage

```bash
seek [OPTIONS] [PATH_OR_SEARCH_TERM] [SEARCH_TERM]
```

## Arguments

| Argument | Description |
| --- | --- |
| `PATH_OR_SEARCH_TERM` | Directory or file to search, or the search term when no matching path exists. Defaults to the current directory. |
| `SEARCH_TERM` | Initial query to seed the search UI. |

---

## Mode selection

The current implementation resolves modes in this order:

1. `--install-dependencies`
2. `--semantic`
3. `--ast`
4. `--file`
5. default text search

That means `seek path query --file --ast` will still take the AST path, and `--install-dependencies` exits before running a search.

---

## Options

| Option | Short | Description |
| --- | --- | --- |
| `--ast` | `-a` | Run AST or tree-sitter symbol search |
| `--semantic` | `-s` | Run semantic search over text chunks with the backend chosen by `--semantic-backend` |
| `--semantic-backend TEXT` | `-b` | Backend for `--semantic`: `semtools` (default), `ck`, `grepai`, or `qmd` |
| `--extension TEXT` | `-E` | Filter file discovery by extension such as `.py`; with `--semantic`, `grepai` rejects it and `qmd` searches `.md` unless it is given |
| `--file` | `-f` | File search mode |
| `--dotfiles` | `-d` | Toggle the dotfile-inclusive file-search path |
| `--rga` | `-A` | Swap `rg` for `rga` in text-search mode |
| `--edit` | `-e` | Open the selected result in Helix |
| `--install-dependencies` | `-i` | Install expected helper tools and exit |
| `--max-files INTEGER` | `-m` | Maximum files for `--semantic` with the `semtools` backend; default is `50`, and `0` disables the limit |

---

## Current behavior by mode

### Text search

The default mode loads a platform-specific helper script and runs an `fzf` + `rg` preview flow.

- `--rga` rewrites that script to use `ripgrep-all`
- `SEARCH_TERM` seeds the initial query
- when the first argument resolves to a directory, StackOps changes to that directory before launching the search

### File search

`--file` runs a file picker based on `fzf`.

- without `--edit`, it previews the file with `bat`
- with `--edit`, it adds a second line picker and opens the selected line in Helix
- by default, the candidate source is `fd --type file`
- with `--dotfiles`, StackOps does not prepend the `fd` candidate source and leaves candidate generation to `fzf`

### Single-file flow

If the first argument resolves to a file, `seek` skips directory search and opens a line-oriented preview for that file instead.

When standard input is piped in and the first argument is a directory, `seek` captures stdin into a temporary file and opens the same single-file flow against that temp file.

### AST search

`--ast` collects repository symbols, shows them with preview, and prints the selected symbol as JSON including:

- type
- name
- path
- file path
- start line
- end line
- docstring

### `--semantic`

`--semantic` searches by meaning instead of keywords and shows up to 10 distinct matches in a preview picker.

- prompts for a query if `SEARCH_TERM` is empty
- overlapping matches from the same file are merged, so each result is a distinct region
- selecting a result prints `path:line`; with `--edit` it opens that line in Helix
- missing backend tools are installed on demand through the installer catalog
- failures such as a missing model, a failed index, or unexpected tool output exit with code `1` and name the backend and stage

Choose the engine with `--semantic-backend` / `-b`:

| Backend | Index | Notes |
| --- | --- | --- |
| `semtools` (default) | cached per directory in a semtools workspace | Static local embeddings, no network. Passes only text files (via `rg`, respecting ignore files) and honours `--extension` and `--max-files`. Also accepts a single file. |
| `ck` | `.ck/` in the searched directory, updated incrementally | Local embeddings, downloaded once on first use. Honours `--extension`. |
| `grepai` | `.grepai/` in the nearest ancestor that has one, otherwise created in the searched directory | Needs an embedding provider; the default is a local Ollama with `nomic-embed-text`. No extension filter. Searching a subdirectory of an indexed project is scoped to it. |
| `qmd` | `.qmd/` in the nearest ancestor that has one, otherwise created in the searched directory | Local GGUF models (about 1.6 GB, downloaded on first use) run query expansion and vector search. Indexes `.md` files unless `--extension` is given. |

`ck`, `grepai`, and `qmd` index directories, so they reject a single-file path. Their index directories are created inside the searched tree, so add them to `.gitignore`.

---

## Dependencies

`seek --install-dependencies` currently installs these helpers:

- `fzf`
- `tv`
- `bat`
- `fd`
- `rg`
- `rga`
- `semtools`

The default `seek --install-dependencies` installs the tools above. Add `-b ck`, `-b grepai`, or `-b qmd` to install that semantic backend instead of `semtools`; the backend tool is also installed on demand the first time you run `--semantic`. `qmd` is installed with `bun install -g @tobilu/qmd`.

---

## Examples

```bash
# Default text search in the current directory
seek

# Seed the search with an initial query
seek . "TODO"

# File search with preview
seek src --file

# File search and open the chosen line in Helix
seek src --file --edit

# AST symbol search
seek src --ast

# Semantic search with the default backend
seek src parser --semantic --extension .py
seek src parser --semantic --extension .py --max-files 200

# Semantic search with another backend, opening the pick in Helix
seek src "retry with backoff" --semantic --semantic-backend ck
seek src "retry with backoff" -s -b qmd -E .py --edit

# ripgrep-all text search
seek docs invoice --rga
```

---

## Getting help

```bash
seek --help
```
