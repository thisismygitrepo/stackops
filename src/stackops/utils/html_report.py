import webbrowser
from html import escape
from pathlib import Path

from stackops.utils.cli_utils.interaction import is_interactive
from stackops.utils.source_of_truth import HTML_REPORTS_ROOT


def show_html_report(*, title: str, payload_json: str, style_path: Path, script_paths: tuple[Path, ...], file_stem: str) -> Path:
    style_text = style_path.read_text(encoding="utf-8")
    script_text = "\n".join(script_path.read_text(encoding="utf-8") for script_path in script_paths)
    embedded_payload = payload_json.replace("<", "\\u003c")
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<style>
{style_text}
</style>
</head>
<body>
<div id="app"></div>
<script id="report-data" type="application/json">{embedded_payload}</script>
<script>
{script_text}
</script>
</body>
</html>
"""
    report_path = HTML_REPORTS_ROOT / f"{file_stem}.html"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.touch(mode=0o600)
    report_path.chmod(0o600)
    report_path.write_text(page, encoding="utf-8")
    if is_interactive():
        webbrowser.open(report_path.as_uri())
    return report_path
