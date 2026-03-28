# Interactive Helpers and Notifications

This part of the API is the human-facing side of `machineconfig`: small helpers for IDs and formatting, interactive selection for CLIs, and notification utilities for sending results outward.

These modules appear inside application logic just as often as they appear in CLI code.

---

## Main modules

| Module | Purpose |
| --- | --- |
| `machineconfig.utils.accessories` | General helpers such as random names, list splitting, timeframe splitting, rich formatting, and repo-root discovery |
| `machineconfig.utils.options` | Interactive option selection with plain prompts or optional Television-based selection |
| `machineconfig.utils.options_utils.tv_options` | Preview-driven selection over a mapping of names to content |
| `machineconfig.utils.notifications` | Markdown-to-HTML conversion and SMTP-based email delivery |

---

## Small but frequently used helpers

`machineconfig.utils.accessories` provides a collection of helpers that show up everywhere:

- `randstr()` for generated identifiers or random noun-style names
- `split_list()` for dividing work into chunks
- `split_timeframe()` for slicing a time interval into fixed pieces
- `pprint()`, `get_repr()`, and `human_friendly_dict()` for readable output
- `get_repo_root()` for locating the current repository root from a path

These functions are small on their own, but they become the glue between higher-level workflows.

---

## Interactive selection flows

`choose_from_options()` gives you a single entrypoint for:

- numbered prompt selection
- optional defaults
- single or multi-select behavior
- Television-backed selection when `tv=True`
- preview integration through `preview="bat"`

`choose_from_dict_with_preview()` is useful when you have a mapping from names to content and want the user to choose while previewing the underlying payload.

### Example

```python
from machineconfig.utils.options import choose_from_options
from machineconfig.utils.options_utils.tv_options import choose_from_dict_with_preview

target = choose_from_options(
    options=["local", "remote", "cloud"],
    msg="Select a target environment",
    multi=False,
    tv=True,
)

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
print(preview_choice)
```

---

## Notifications

`machineconfig.utils.notifications.Email` wraps a simple SMTP-based workflow:

- load email settings from a local INI file
- optionally convert Markdown bodies into HTML
- send a message
- close the connection cleanly

That makes it a natural fit for job-completion notices, summary reports, and operational alerts.

```python
from machineconfig.utils.notifications import Email

Email.send_and_close(
    config_name="primary",
    to="team@example.com",
    subject="Job finished",
    body="# Completed\nAll tasks finished successfully.",
)
```

---

## API reference

## Accessories

::: machineconfig.utils.accessories
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Options

::: machineconfig.utils.options
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Preview selection

::: machineconfig.utils.options_utils.tv_options
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Notifications

::: machineconfig.utils.notifications
    options:
      show_root_heading: true
      show_source: false
      members_order: source
