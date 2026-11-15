from rich.filesize import decimal

from stackops.scripts.python.helpers.helpers_utils.clean_drive_constants import PICKER_PREVIEW_PERCENT, PREVIEW_PATH_LIMIT
from stackops.scripts.python.helpers.helpers_utils.clean_drive_models import TargetScan
from stackops.scripts.python.helpers.helpers_utils.clean_drive_render import describe_action, format_estimate, ready_by_size
from stackops.scripts.python.helpers.helpers_utils.clean_drive_scan import requires_root
from stackops.utils.options_utils.tv_options import choose_from_dict_with_preview


def _preview(*, scan: TargetScan, elevated: bool) -> str:
    target = scan.target
    shown = scan.paths[:PREVIEW_PATH_LIMIT]
    path_lines = "\n".join(f"""- `{measured.path}` — {decimal(measured.bytes)}""" for measured in shown)
    hidden = len(scan.paths) - len(shown)
    more = f"""\n- … and {hidden} more""" if hidden > 0 else ""
    paths_section = f"""\n\n## Paths\n{path_lines}{more}""" if shown else ""
    return f"""# {target.title}

- **Savings:** {format_estimate(scan.estimate)}
- **Risk:** {target.risk}
- **Category:** {target.category.value}
- **Needs root:** {"yes" if requires_root(scan.action) else "no"}
- **Action:** {describe_action(scan=scan, elevated=elevated)}

{target.note}{paths_section}
"""


def pick_scans(*, scans: list[TargetScan], elevated: bool) -> list[TargetScan]:
    options = {
        f"""{format_estimate(scan.estimate):>12}  {scan.target.risk:<7}  {scan.target.key}""": (scan.target.key, _preview(scan=scan, elevated=elevated))
        for scan in ready_by_size(scans)
    }
    chosen_labels = choose_from_dict_with_preview(
        {label: preview for label, (_key, preview) in options.items()}, extension="md", multi=True, preview_size_percent=PICKER_PREVIEW_PERCENT,
    )
    chosen_keys = {options[label][0] for label in chosen_labels}
    return [scan for scan in scans if scan.target.key in chosen_keys]
