from typing import Final

# The pages are rendered here rather than kept as .html files: the repository ignores *.html, so a page on disk never reaches a clone or a wheel.
APP_STYLESHEETS: Final[tuple[str, ...]] = (
    "/assets/app/styles/base.css",
    "/assets/app/styles/shell.css",
    "/assets/app/styles/widgets.css",
    "/assets/app/styles/overlays.css",
    "/assets/app/styles/spaces.css",
    "/assets/app/styles/reports.css",
    "/assets/app/styles/app_updates.css",
    "/assets/app/styles/agents_running.css",
    "/assets/app/styles/agents_prompts.css",
    "/assets/app/styles/agents_health.css",
    "/assets/app/styles/agents_workbench.css",
    "/assets/app/styles/disk_cleanup.css",
    "/assets/app/styles/security.css",
    "/assets/app/styles/vault.css",
    "/assets/app/styles/scripts.css",
)
DEVELOPER_STYLESHEETS: Final[tuple[str, ...]] = (
    "/assets/styles/base.css",
    "/assets/styles/shell.css",
    "/assets/styles/views.css",
    "/assets/styles/panels.css",
)


def render_page(stylesheets: tuple[str, ...], script: str, boot_note: str) -> str:
    stylesheet_links = "\n".join(f"""<link rel="stylesheet" href="{stylesheet}">""" for stylesheet in stylesheets)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>StackOps</title>
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
{stylesheet_links}
</head>
<body>
<div id="app"><p class="boot-note">{boot_note}</p></div>
<script type="module" src="{script}"></script>
</body>
</html>
"""


APP_PAGE: Final[str] = render_page(stylesheets=APP_STYLESHEETS, script="/assets/app/scripts/entry.js", boot_note="Getting things ready…")
DEVELOPER_PAGE: Final[str] = render_page(stylesheets=DEVELOPER_STYLESHEETS, script="/assets/scripts/main.js", boot_note="Loading StackOps…")
