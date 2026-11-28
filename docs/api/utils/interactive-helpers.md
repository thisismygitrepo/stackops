# Interactive Helpers

This slice of the utility API covers the parts of StackOps that talk directly to a person: small formatting helpers and interactive pickers.

The current modules are:

| Module | Purpose |
| --- | --- |
| `stackops.utils.accessories` | Small shared helpers such as random strings, list/timeframe splitting, rich formatting, and git-root discovery |
| `stackops.utils.options_utils.options` | Terminal choice helpers, plus cloud and SSH selectors |
| `stackops.utils.options_utils.tv_options` | Preview-based selection from a mapping of names to payloads |

---

## `accessories`

Frequently used helpers from `stackops.utils.accessories` include:

- `randstr()` for random tokens or noun-style names
- `split_list()` for chunking lists by size or number of buckets
- `split_timeframe()` for splitting a UTC interval into fixed windows
- `pprint()`, `get_repr()`, and `human_friendly_dict()` for human-readable output
- `get_repo_root()` for locating the git repository root from a `Path`

These are intentionally small, but they show up throughout the CLI and helper layers.

---

## `choose_from_options`

`stackops.utils.options_utils.options.choose_from_options()` is the main interactive picker.

Current behavior:

- requires an interactive terminal: it first calls `require_interactive()` from `stackops.utils.cli_utils.interaction`, which raises a usage error when stdin or stdout is not a TTY or `STACKOPS_NON_INTERACTIVE` is set
- accepts any iterable of options and returns `None` when the list is empty or nothing is selected
- supports a numbered prompt fallback
- can use Television when `tv=True` and `tv` is installed
- supports `preview="bat"` for Television-backed previews
- accepts an optional default item
- allows custom string input when `custom_input=True`

Two implementation details matter in practice:

- the default must already be present in the option list
- multi-select is primarily implemented through the Television path; the plain prompt fallback still behaves like a single-choice prompt

Other exported helpers in the same module:

- `choose_cloud_interactively()` runs `rclone listremotes` and lets the user choose a remote
- `get_ssh_hosts()` parses `~/.ssh/config` with Paramiko
- `choose_ssh_host()` builds a Television-backed picker on top of that SSH host list

Example:

```python
from stackops.utils.options_utils.options import choose_from_options, choose_ssh_host
from stackops.utils.options_utils.tv_options import choose_from_dict_with_preview

target = choose_from_options(
    options=["local", "remote", "cloud"],
    msg="Select a target",
    multi=False,
    tv=True,
    preview=None,
)

ssh_host = choose_ssh_host(multi=False)

preview_choice = choose_from_dict_with_preview(
    {
        "README.md": "# Example\n",
        "config.toml": "workers = 8\n",
    },
    extension="md",
    multi=False,
    preview_size_percent=60,
)

print(target)
print(ssh_host)
print(preview_choice)
```

---

## Preview selection

`stackops.utils.options_utils.tv_options.choose_from_dict_with_preview()` is the lower-level preview helper used by AST search, the interactive installer picker, session pickers, and other payload-preview flows.

It takes four required arguments:

- `options_to_preview_mapping`, a mapping from option label to preview content
- `extension`, an extension hint or `None`
- `multi=True` or `False`
- `preview_size_percent`

Like `choose_from_options()`, it calls `require_interactive()` first. An empty mapping returns `[]` when `multi=True` and `None` otherwise.

The implementation dispatches to Windows- or Unix-specific Television helpers. Unix preview scratch files are written under
`~/tmp_results/tmp_files` by default; set `STACKOPS_TV_TEMP_DIR` to override that location.

---

## API reference

## Accessories

::: stackops.utils.accessories
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Options

::: stackops.utils.options_utils.options
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Preview selection

::: stackops.utils.options_utils.tv_options
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Textual options form

::: stackops.utils.options_utils.textual_options_form
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Textual options form types

::: stackops.utils.options_utils.textual_options_form_types
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Terminal helpers

::: stackops.utils.cli_utils.terminal
    options:
      show_root_heading: true
      show_source: false
      members_order: source
