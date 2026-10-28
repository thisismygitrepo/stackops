# Changing StackOps

Use this guide when a user asks to add, edit, rename, or remove something. Command examples use installed entrypoints; in the StackOps checkout, prefix them with `UV_CACHE_DIR=/tmp/uv-cache uv run`. Discover configuration from the target project, or pass its explicit file path when running elsewhere.

## Choose the owning layer

| Requested result | Where to start |
| --- | --- |
| Another layout/tab, saved prompt, repository, installer, MCP server, or mapping | The active configuration file and its schema, using the commands below |
| Change a supported setting or an entry's existing field | The selected configuration source; inspect the loader if precedence is unclear |
| Support a new field, command, option, or behavior | The command registration and callback, then its implementation and any affected parser/types/schema |
| Change a bundled default or example for all users | The source asset used by the loader; distinguish it from a user's active configuration |

Identify the target project, source, and entry from the request and current files. Ask only when ambiguity changes the edit, such as two layouts with the same name in different sources. Preserve the requested operation: do not turn removal into disabling, or an extra tab into a new CLI command.

## Locate configuration and its contract

Run the relevant command's `--help`, then its `path` command. The JSON output identifies `path` (the editable data), `schema` (the bundled contract), and `local_schema` (the adjacent editor schema). A reported path can refer to a file that does not exist yet. Follow applicable access restrictions before reading any resolved path; a command that enumerates multiple sources can read files outside the intended scope.

| Configuration | Discovery command | Source selection |
| --- | --- | --- |
| StackOps settings | `devops config path config` | `--custom-path` for an explicit file |
| Terminal layouts and tabs | `terminal path` | `--source project` (alias `p`), `--source user` (alias `u`), or `--custom-path` |
| Dotfile mappings | `devops config dotfiles path` | `--custom-path` for an explicit file |
| Data/backup mappings | `devops data path` | `--custom-path` for an explicit file |
| Secrets | `devops vault path` | `--source project` (alias `p`), `--source user` (alias `u`), or `--custom-path` |
| Repository specifications | `devops repos path` | `--path` for an explicit file |
| Software installers | `devops software path` | `--source user`, `library`, or `all`; `--custom-path` replaces the user catalog |
| Saved prompts | `agents config path prompts` | `--source project` (alias `p`), `--source user` (alias `u`), `--source library` (alias `l`), or `--custom-path` |
| Parallel agent workflows | `agents config path parallel` | Same agent source selection |
| MCP catalog | `agents config path mcp` | Same agent source selection |

Read the selected data file and the reported bundled schema before editing. Inspect the loader when a source override, name lookup, or cross-reference matters. In particular, deleting a software user override exposes the bundled entry again; it does not uninstall software or remove the bundled definition. Agent catalogs can also combine sources: check the consuming command's source selection before claiming an entry is gone.

An explicit management file selects the file to edit or validate; it does not make a later runtime command consume that file. Generic `devops config` management and the dotfile/data file-management commands use `--custom-path` for an explicit file. Agent catalog, vault, and terminal layout commands also use `--custom-path`, which selects only that file even when `--source` is supplied. Software commands use `--custom-path` to replace the user catalog: `--source all` still merges it with the library catalog, and `--source library` cannot be combined with a custom path. Standalone `devops repos` management commands retain `--path`; generic `devops config ... repos` uses `--custom-path`. StackOps settings currently load from `DOTFILES_STACKOPS_CONFIG_PATH` in `src/stackops/utils/source_of_truth.py`. For saved prompts, `agents run-prompt --source project` can also discover files in the working directory and immediate child directories, including outside Git, beyond the root file reported by `agents config path prompts`. Trace an existing prompt to its actual source before editing or creating a same-named entry elsewhere.

`devops config dotfiles register` and `devops data register` support only `--source user`, the default. Both use `-s` for `--source`. Dotfile registration stores files in the user `mapper/files` directory by default, with `--destination` for an explicit storage directory. Dotfile sync uses `--source` / `-s` to select user, library, or all mappings and processes all entries selected by that source and `--which`. Software `init`, `edit`, and `validate` also accept only `--source user`, their default; software `list`, `install`, and `path` retain the user, library, and all choices.

To consume a custom agent catalog, pass `--custom-path` to `agents run-prompt`, `agents parallel run`, or `agents add-mcp`. Their sources are `project/p`, `user/u`, `library/l`, or `all/a`. `agents parallel run --prompt-path` still supplies prompt text, not the workflow YAML. Vault `search`, `load`, and `stats` accept `project/p`, `user/u`, or `all/a`; a custom path overrides all of them. MCP and skill installation use `--scope project` (alias `p`) or `--scope user` (alias `u`) for their destination, separately from catalog source selection. `agents reset --scope` also accepts `all/a`.

`terminal run`, `run-all`, and `list` accept `--source` / `-s` with `project/p`, `user/u`, or `all/a`, defaulting to `all`. The default includes available user and Git-project layout files; outside Git it includes only the user file. Explicit `--source project` requires a Git repository. These commands and `terminal path`, `edit`, `init`, and `validate` accept `--custom-path` / `-p`, which overrides source selection, including outside Git. `terminal run --parallel-layouts` uses `-j`, `terminal run-all --poll-interval` uses `-i`, and `terminal list --stats` uses `-S`.

Use `init` for a missing file when creation is part of the request. It creates a schema and initial content, which may include example entries. For an agent making the edit, patch the selected file directly; interactive `edit` commands are available for a human editor workflow. Keep unrelated entries, ordering, metadata, and comments intact where the format permits them.

- **Add:** locate the containing list or mapping, check for an existing identity, and insert the requested entry with fields required by the schema.
- **Edit or rename:** match the existing identity, change the requested fields, and adjust references that must follow the rename. Check for a conflicting new name.
- **Remove:** remove the selected entry and references that would otherwise become invalid. Check required fields and collection minimums before leaving an empty parent.

Validate the exact edited file. Each family above has a `validate` command; agent kinds follow the action, as in `agents config validate prompts --custom-path /absolute/prompts.yaml`. Vault validation uses `devops vault validate --custom-path /absolute/secrets.json`. The common form for every managed kind is `devops config validate KIND --custom-path /absolute/file`, where `KIND` is `config`, `layouts`, `dotfiles`, `data`, `secrets`, `repos`, `software`, `prompts`, `parallel`, or `mcp`. Confirm flags with live help.

Report the file, selected entry, change, and validation result. For secret edits, report keys and paths without exposing values. Applying a configuration is a separate operation: saving a layout does not launch it, and editing an MCP catalog does not install it into an agent's settings.

## Example: add, edit, or remove a layout entry

1. From the target project, use `terminal path --source project`, or `terminal path --custom-path /absolute/layout.json` for an explicitly requested file. A project layout is `.stackops/config/layout.json` under the enclosing Git repository root, including when called from a subdirectory. Resolve a user target through `terminal path --source user` when that is the requested source. Outside Git, use the user source or an explicit file.
2. Read the chosen file and its reported schema. `terminal list --custom-path /absolute/layout.json --tabs` shows layouts and tabs from just that file. For a standard source, use `terminal list --source project --tabs` or `--source user`; omitting both the custom path and source lists all available default sources.
3. Find the exact `layoutName` in the top-level `layouts` array. An extra tab goes in that layout's `layoutTabs`; a whole new layout is another object in `layouts`.

A tab has this shape; take its name, directory, and command from the request or the project:

```json
{
  "tabName": "worker",
  "startDir": "/absolute/project",
  "command": "uv run worker.py"
}
```

`tabWeight` is optional. A new layout needs both `layoutName` and `layoutTabs`. Preserve the file's `version` and optional `$schema`. Edit a tab by its name within the chosen layout, and remove only the requested tab or layout. The current schema requires at least one layout and at least one tab per layout; if the requested deletion would empty one, resolve the intended remaining configuration instead of inventing a placeholder entry.

Finish with `terminal validate --custom-path /absolute/layout.json`. This validates the schema and parser without launching sessions. An added tab using existing fields requires only the data edit. If the request introduces a new field or changes launch behavior, trace these source owners:

- `src/stackops/scripts/python/terminal.py`: registrations and launch callbacks.
- `src/stackops/scripts/python/terminal_layout_files.py`: path, init, and validate commands.
- `src/stackops/scripts/python/helpers/helpers_sessions/sessions_layout_source.py`: source selection and layout-name resolution.
- `src/stackops/scripts/python/helpers/helpers_sessions/sessions_impl.py`: parsing and backend dispatch.
- `src/stackops/utils/schemas/layouts/layout_types.py` and `layout.schema.json`: data types and schema.

The layout serializer's `merge_by_layout_name` replaces a whole matching layout. To add a tab, preserve the existing tabs in that layout rather than passing a one-tab replacement.

## When the request needs code

Resolve the checkout and find the direct entrypoint's module in `pyproject.toml` `[project.scripts]`, indexed by [cli-map.md](cli-map.md). The [source-map.md](source-map.md) follows the umbrella command's dispatch routes; direct commands do not start in `stackops_entry.py`. Follow Typer registration from the actual entrypoint to the callback and its lazy imports. Use `rg` for the command, field, or configuration key in that part of `src/stackops/`; a root dispatcher or graph entry alone is not the implementation.

- **Add:** extend the actual registration/callback/helper or the data contract and consumer, as required by the feature. Reuse the surrounding lazy-routing pattern.
- **Edit:** change the owning implementation and any signature, parser, or schema that must agree with it.
- **Remove:** for a command, remove its registration and hidden aliases, then references and implementation used only by that command. For an option or data field, remove its definition and value handling while preserving the surrounding command; keep the parser/types/schema and consumer consistent.

Choose an existing focused check that demonstrates the requested change under the repository's validation rules. Help verifies CLI discovery and signatures, not runtime behavior. Refresh generated CLI maps with `devops self build-assets skill-refs` only when the CLI shape changes. Generated maps, docs, and installed copies are not the source to edit for a behavior change.
