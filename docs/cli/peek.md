# peek

`peek` is the direct entrypoint for interactive search across files, text matches, and code symbols.

---

## Usage

```bash
peek [OPTIONS] [PATH] [SEARCH_TERM]
```

---

## Arguments

| Argument | Description |
|----------|-------------|
| `PATH` | Directory or file to search. Defaults to the current directory. |
| `SEARCH_TERM` | Initial query to seed the interactive search UI. |

---

## Search modes

`peek` exposes several entry modes:

| Mode | Option | Behavior |
|------|--------|----------|
| Text search | default | Interactive ripgrep-based search with preview |
| File search | `--file`, `-f` | Fuzzy-find files with preview |
| AST search | `--ast`, `-a` | Inspect parsed symbols from the target directory |
| Symantic search | `--symantic`, `-s` | Run the symbol-oriented helper workflow |

If `PATH` points to a file, `peek` opens a line-oriented preview flow for that file instead of directory search.

When multiple mode flags are passed together, `peek` resolves them in this order: `--symantic`, then `--ast`, then `--file`, then the default text search flow.

---

## Options

| Option | Short | Description |
|--------|-------|-------------|
| `--ast` | `-a` | Run abstract syntax tree or tree-sitter symbol search |
| `--symantic` | `-s` | Run symantic symbol search |
| `--extension TEXT` | `-E` | Filter by extension such as `.py` or `.js` |
| `--file` | `-f` | Search for files instead of text matches |
| `--dotfiles` | `-D` | Include dotfiles in file search results |
| `--rga` | `-A` | Use `ripgrep-all` instead of `ripgrep` |
| `--edit` | `-e` | Open the selected match in Helix |
| `--install-req` | `-i` | Install required search dependencies |

---

## Typical flows

```bash
# Search the current project for text
peek

# Start with an initial query
peek . "TODO"

# Search for files only
peek src --file

# Search files including dotfiles
peek src --file --dotfiles

# Search files and jump into Helix
peek src --file --edit

# Search code symbols
peek src --ast

# Use ripgrep-all for non-text files
peek docs --rga
```

---

## Notes

- `peek --install-req` installs the helper tools the workflow expects, including `fzf`, `tv`, `bat`, `fd`, `rg`, and `rga`.
- When standard input is piped into `peek`, it can stage that input into a temporary file and open the same preview flow against the captured content.
- `peek` is a standalone entrypoint. Use it directly rather than routing through an umbrella dispatcher.

---

## Getting help

Use live help to inspect the exact options in your installed version:

```bash
peek --help
```
