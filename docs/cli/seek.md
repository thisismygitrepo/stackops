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
| `SEARCH_TERM` | Search query; seeds the search UI unless `--json` is used. |

---

## Mode selection

The current implementation resolves modes in this order:

1. `--install-dependencies`
2. `--semantic`
3. `--ast`
4. `--file`
5. default text search

That means `seek path query --file --ast` will still take the AST path, and `--install-dependencies` exits before running a search.

`--json` keeps the same order but prints the results of the chosen mode as a JSON array instead of opening a picker. Without `--json`, every search mode needs an interactive terminal on both standard input and standard output; the one exception is text piped into the default text search, described under the single-file flow.

---

## Options

| Option | Short | Description |
| --- | --- | --- |
| `--ast` | `-a` | Run AST or tree-sitter symbol search |
| `--semantic` | `-s` | Run semantic search over text chunks with the backend chosen by `--semantic-backend` |
| `--semantic-backend TEXT` | `-b` | Backend for `--semantic`: `ck` (default), `grepai`, `qmd`, or `semtools` |
| `--extension TEXT` | `-E` | Filter file discovery by extension such as `.py`; with `--semantic`, `grepai` rejects it and `qmd` searches `.md` unless it is given |
| `--file` | `-f` | File search mode |
| `--dotfiles` | `-d` | Toggle the dotfile-inclusive file-search path |
| `--rga` | `-A` | Swap `rg` for `rga` in text-search mode |
| `--edit` | `-e` | Open the selected result in Helix |
| `--json` | `-j` | Print a JSON array without prompts or a picker. Text and semantic searches require a query; file and AST searches allow an empty one. Missing tools are not installed automatically. Cannot be combined with `--edit` or `--install-dependencies` |
| `--install-dependencies` | `-i` | Install expected helper tools and exit |
| `--non-interactive` | `-N` | Disable interactive selection; use `--json` for search results |
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

When text is piped in and the first argument is a directory, the default text search captures stdin into a temporary file and opens the same single-file flow against it, for example `git log --oneline | seek`. Standard output must still be a terminal; an empty pipe, `--non-interactive`, `STACKOPS_NON_INTERACTIVE`, and the `--ast`, `--semantic` and `--file` modes are refused without `--json`.

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
- missing backend tools are installed on demand through the installer catalog (not with `--json`, which reports them instead)
- failures such as a missing model, a failed index, or unexpected tool output exit with code `1` and name the backend and stage

Choose the engine with `--semantic-backend` / `-b`:

| Backend | Index | Notes |
| --- | --- | --- |
| `ck` (default) | `.ck/` in the searched directory, updated incrementally | Local embeddings, downloaded once on first use. Honours `--extension`. |
| `grepai` | `.grepai/` in the nearest ancestor that has one, otherwise created in the searched directory | Needs a local embedding provider; a new index is initialized for Ollama (`nomic-embed-text`). An existing config is used only when it embeds with Ollama or LM Studio on a loopback endpoint into the local `gob` store. No extension filter. Searching a subdirectory of an indexed project is scoped to it. |
| `qmd` | `.qmd/` in the nearest ancestor that has one, otherwise created in the searched directory | Local GGUF models (about 1.6 GB, downloaded on first use) run query expansion and vector search. Indexes `.md` files unless `--extension` is given. |
| `semtools` | cached per directory in a semtools workspace | Static local embeddings, no network. Passes only text files (via `rg`, respecting ignore files) and honours `--extension` and `--max-files`. Also accepts a single file. |

`ck`, `grepai`, and `qmd` index directories, so they reject a single-file path. Their index directories are created inside the searched tree. `seek` writes a `.gitignore` into the `.ck/` and `.qmd/` directories it creates so they stay out of Git; `.grepai/` is left to grepai, so check that it is ignored.

---

## Dependencies

`seek --install-dependencies` currently installs these helpers:

- `fzf`
- `tv`
- `bat`
- `fd`
- `rg`
- `rga`
- `ck`

The default `seek --install-dependencies` installs the tools above. Add `-b grepai`, `-b qmd`, or `-b semtools` to install that semantic backend instead of `ck`; the backend tool is also installed on demand the first time you run `--semantic`. `qmd` is installed with `bun install -g @tobilu/qmd`.

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

# Semantic search with another backend, opening the pick in Helix
seek src parser --semantic --semantic-backend semtools --extension .py --max-files 200
seek src "retry with backoff" -s -b qmd -E .py --edit

# ripgrep-all text search
seek docs invoice --rga

# JSON results without a picker
seek src "TODO" --json
seek src --file --json
```

---

## Getting help

```bash
seek --help
```
