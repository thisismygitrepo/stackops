# Layouts

The layout APIs turn Python intent into terminal structure. They define tabs and panes, serialize layouts, build tab commands from callables, and split oversized layouts before handing them to the tmux backend.

---

## Layout schema

The types live in `stackops.utils.schemas.layouts.layout_types`; reading and writing layout files lives in `stackops.utils.schemas.layouts.layout_file`. Layout files are YAML with the `.yaml` suffix and `version: "0.2"`.

### Core types

| Type | Fields |
| --- | --- |
| `PaneConfig` | `paneName`, `startDir`, `command`, optional `enabled` |
| `TabConfig` | `tabName`, `panes`, optional `arrangement` (`columns`, `rows`, or `grid`), optional `tabWeight`, optional `enabled` |
| `LayoutConfig` | `layoutName`, `layoutTabs`, optional `enabled` |
| `LayoutsFile` | `version` (always `"0.2"`), `layouts` |

### Helper behavior

- `read_layouts_file(path)` parses and validates a `.yaml` layout file; any other suffix, a `version` other than `"0.2"`, or a malformed layout, tab or pane (including an empty `panes` list, a `paneName` repeated within a tab, or a non-boolean `enabled`) raises `ValueError`.
- `write_layouts_file(path, layouts_file)` writes YAML headed by `# yaml-language-server: $schema=https://raw.githubusercontent.com/thisismygitrepo/stackops/refs/heads/main/src/stackops/utils/schemas/layouts/layout.schema.json`.
- `serialize_layouts_to_file(layouts, path, write_mode="replace_file")` writes the layouts and replaces any existing file content.
- `serialize_layouts_to_file(layouts, path, write_mode="merge_by_layout_name")` preserves existing layouts, replaces layouts that share the same `layoutName`, and appends new layout names. A replaced layout keeps the tabs and panes that were switched off (`enabled: false`) in the layout it replaces.
- Both write modes raise `ValueError` when the layouts passed in repeat a `layoutName`.
- `single_pane_tab(tab_name=..., start_dir=..., command=...)` builds a tab with one pane named after the tab.
- `substitute_home(tabs)` expands `~` and `$HOME` and rewrites shorthand command prefixes:
  - `f ...` -> `~/.config/stackops/scripts/wrap_stackops fire ...`
  - `t ...` -> `~/.config/stackops/scripts/wrap_stackops terminal ...`
  - `s ...` -> `~/.config/stackops/scripts/wrap_stackops seek ...`

The current schema keys are `layoutTabs` and `panes`. There is no alternate `tabs` field, and a tab carries no `startDir` or `command` of its own.

### Empty commands

A pane's `paneName`, `startDir`, and `command` must be present and must be strings, but `read_layouts_file()` and `layout.schema.json` both accept an empty string. Those two are what validate a layout file (`terminal validate`, `devops config validate layouts`), including one created from the packaged `layout.example.yaml`, whose only pane has `command: ""`.

The tmux layer is stricter. `validate_layout_config()` in `tmux_utils.tmux_layout` raises `ValueError` for a pane whose `paneName`, `command`, or `startDir` is empty or only whitespace, and it runs in `TmuxLayoutGenerator.create_layout_file()`, `build_tmux_commands()`, and `build_tmux_merge_commands()`. A pane with an empty command therefore passes file validation and fails when the layout is handed to tmux; give it a command first.

### Switching entries off

`enabled` defaults to `true` on a layout, a tab, and a pane. Two modules work with it:

- `stackops.utils.schemas.layouts.layout_enabled.drop_disabled(layouts)` returns what a launch opens: it leaves out every layout, tab, and pane that is switched off, plus any tab or layout left empty, and raises `ValueError` when nothing remains.
- `stackops.utils.schemas.layouts.layout_enabled_edit.switch_layout_entry(path, target, enabled)` flips one entry of a layout file in place, leaving comments and formatting alone. It returns `None` on success or a `LayoutSwitchFailure` whose `reason` is `invalid_file`, `entry_gone`, or `unsupported_format`.

The tmux helpers below launch whatever they are handed, so pass layouts through `drop_disabled()` first when switched-off entries should be left out.

---

## Building layouts from Python functions

`stackops.cluster.sessions_managers.utils.maker` converts Python functions into `TabConfig` entries.

### Main helpers

| Helper | Purpose |
| --- | --- |
| `get_fire_tab_using_uv()` | Generates Python source from a function, writes a temporary script under `~/tmp_results/tmp_scripts/python/`, and returns the tab config plus the generated file path |
| `get_fire_tab_using_fire()` | Builds a `wrap_stackops fire run ...` command for a function file under the user's home directory |
| `make_layout_from_functions()` | Builds a `LayoutConfig` from functions plus any extra tabs you want to append |

`make_layout_from_functions()` accepts both launch styles through `method`:

- `"script"` to execute generated Python through `uv`
- `"fire"` to use the `wrap_stackops fire run` entrypoint

Its `flags` parameter is passed through to the selected launch mode as either `uv_run_flags` or `fire_flags`. In `"script"` mode `--no-sync` is always placed in front of those flags.

Set `max_stagger` to add a random startup delay of up to that many seconds to each generated function tab, and to every pane of the extra `tab_configs` whose command starts a Python process (`uv`, `python`, `fire`, `wrap_stackops fire`, and similar launchers). The delayed command also runs with `UV_NO_SYNC=1`. The extra delay is applied after the helper returns the tab command, so `get_fire_tab_using_uv()` and `get_fire_tab_using_fire()` keep their direct command behavior unchanged. Negative values raise `ValueError`; `max_stagger` is the only optional parameter and defaults to `None` (no delay).

### Where the functions live

In `"script"` mode each tab runs a generated script whose top-level code is the body of the function. With `import_module=True` that script first imports everything from the file that defines the function (`from <module> import *`, adding the file's folder to `sys.path` when the plain import fails), so the body can use the module's other names.

Keep the functions in a module that is safe to import. A function defined in the launching script itself makes every tab import that script, which runs its top-level code again, the launch included, unless that code sits under `if __name__ == "__main__":`.

### Example

`jobs.py`, next to the launcher:

```python
def ingest() -> None:
    print("ingest")


def train() -> None:
    print("train")
```

The launcher:

```python
from jobs import ingest, train
from stackops.cluster.sessions_managers.tmux.tmux_local import run_tmux_layout
from stackops.cluster.sessions_managers.utils.maker import make_layout_from_functions

layout = make_layout_from_functions(
    functions=[ingest, train],
    functions_weights=[1, 2],
    import_module=True,
    tab_configs=[],
    layout_name="ml-workflow",
    method="script",
    uv_with=["stackops"],
    uv_project_dir=None,
    flags="",
    start_dir="~/code/my-project",
    max_stagger=10.0,
)

run_tmux_layout(layout_config=layout, on_conflict="rename")
```

If `functions_weights` is `None`, each function is treated as weight `1`.

---

## Controlling layout size

`stackops.cluster.sessions_managers.utils.load_balancer` provides two controls.

### `limit_tab_num()`

```python
limit_tab_num(
    layout_configs=layouts,
    max_thresh=8,
    threshold_type="number",
    breaking_method="moreLayouts",
)
```

Supported `threshold_type` values:

- `"number"` for raw tab count
- `"weight"` for summed `tabWeight`

Supported `breaking_method` values:

- `"moreLayouts"`
- `"combineTabs"`

`max_thresh` below `1` raises `ValueError`. `"combineTabs"` joins the commands of several tabs into one `super_tab_N` tab, so the tabs it combines must each have a single pane.

### `limit_tab_weight()`

`limit_tab_weight(layout_configs, max_weight, command_splitter)` rewrites overweight tabs by calling your `command_splitter(command, to=max_weight)` function and replacing the original tab with `..._part1`, `..._part2`, and so on. An overweight tab must have a single pane.

### Convenience launcher

`load_balancer.run(layouts, on_conflict)` is a thin helper that:

1. creates a `TmuxLocalManager` with no session-name prefix and `exit_mode="backToShell"`
2. starts all sessions with the given `on_conflict` policy
3. runs the monitoring routine at 2-second intervals
4. kills the sessions it started when monitoring finishes

---

## Backend-specific layout generators

The same `LayoutConfig` can be handed to the tmux backend:

- `run_tmux_layout(layout_config, on_conflict)` using `exit_mode="backToShell"`

The generator class is:

- `TmuxLayoutGenerator`

That class is responsible for rendering backend-specific layout artifacts:

- tmux launch scripts under `~/tmp_results/sessions/tmux_layouts/` (`.sh`, or `.ps1` on Windows)

---

## API reference

## Layout schema reference

::: stackops.utils.schemas.layouts.layout_types
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Layout files

::: stackops.utils.schemas.layouts.layout_file
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Layout constants

::: stackops.utils.schemas.layouts.layout_constants
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Enabled entries

::: stackops.utils.schemas.layouts.layout_enabled
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Enabled switch editing

::: stackops.utils.schemas.layouts.layout_enabled_edit
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Arrangement inference

::: stackops.utils.schemas.layouts.layout_arrangement
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Layout builders

::: stackops.cluster.sessions_managers.utils.maker
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Layout load balancer

::: stackops.cluster.sessions_managers.utils.load_balancer
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Load balancer helper

::: stackops.cluster.sessions_managers.helpers.load_balancer_helper
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## tmux layout generator

::: stackops.cluster.sessions_managers.tmux.tmux_local
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## tmux common helpers

::: stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_common
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## tmux execution helpers

::: stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_execution
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## tmux layout helpers

::: stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_layout
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## tmux status helpers

::: stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_status
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## tmux launch table

::: stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_launch_table
    options:
      show_root_heading: true
      show_source: false
      members_order: source
