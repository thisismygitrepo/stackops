from collections import Counter
from typing import assert_never, cast, get_args

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.text import Text

from stackops.profile.dotfiles_collect_plan import CollectEntryPlan, VerdictCategory, verdict_category
from stackops.profile.dotfiles_constants import STATUS_DETAIL_ROW_LIMIT, OsName
from stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_collect import describe_verdict
from stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_mapper import format_home_relative_path
from stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_status_render import detail_table


def _describe_category(category: VerdictCategory) -> str:
    match category:
        case "collectable":
            return "collectable"
        case "skipped":
            return "skipped by collect"
        case "tracked":
            return "in your mapper"
        case "packaged":
            return "same as the packaged settings"
        case "absent":
            return "not on this machine"
        case "other_os":
            return "for another OS"
        case _:
            assert_never(category)


def render_radar(plans: list[CollectEntryPlan], current_os: OsName, expand: bool) -> Panel:
    ordered_categories = cast(tuple[VerdictCategory, ...], get_args(VerdictCategory.__value__))
    categories: Counter[VerdictCategory] = Counter(verdict_category(plan.verdict) for plan in plans)
    summary = Text(" · ".join(f"""{categories[category]} {_describe_category(category)}""" for category in ordered_categories if categories[category] > 0), style="dim")
    untracked = [plan for plan in plans if verdict_category(plan.verdict) in ("collectable", "skipped")]
    parts: list[RenderableType] = [summary]
    if expand:
        details = detail_table("Category", "Entry", "Original", "Collect would")
        on_this_os = [plan for plan in plans if verdict_category(plan.verdict) != "other_os"]
        for plan in sorted(on_this_os, key=lambda plan: ordered_categories.index(verdict_category(plan.verdict))):
            category = _describe_category(verdict_category(plan.verdict))
            details.add_row(category, f"""{plan.group}.{plan.name}""", format_home_relative_path(plan.original_path), describe_verdict(plan.verdict))
        parts.append(details)
    elif 0 < len(untracked) <= STATUS_DETAIL_ROW_LIMIT:
        details = detail_table("Group", "Entry", "Original", "Collect would")
        for plan in untracked:
            details.add_row(plan.group, plan.name, format_home_relative_path(plan.original_path), describe_verdict(plan.verdict))
        parts.append(details)
    elif len(untracked) > STATUS_DETAIL_ROW_LIMIT:
        details = detail_table("Group", "Entries", "Collect would")
        for group in dict.fromkeys(plan.group for plan in untracked):
            group_plans = [plan for plan in untracked if plan.group == group]
            details.add_row(group, ", ".join(plan.name for plan in group_plans), "; ".join(dict.fromkeys(describe_verdict(plan.verdict) for plan in group_plans)))
        parts.append(details)
    collectable_groups = list(dict.fromkeys(plan.group for plan in untracked if verdict_category(plan.verdict) == "collectable"))
    if len(collectable_groups) > 0:
        parts.append(Text(f"""Collect with: devops config dotfiles collect --which {",".join(collectable_groups)}""", style="dim"))
    return Panel(
        Group(*parts),
        title=f"""📡 Known dotfiles on {current_os} ({categories["collectable"]} collectable, {categories["skipped"]} skipped)""",
        border_style="green" if len(untracked) == 0 else "yellow",
        expand=True,
    )
