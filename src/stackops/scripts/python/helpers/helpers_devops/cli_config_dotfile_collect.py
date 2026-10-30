from typing import TYPE_CHECKING, Annotated, Never, assert_never

import typer

if TYPE_CHECKING:
    from stackops.profile.dotfiles_collect_plan import CollectEntryPlan, CollectVerdict

COLLECT_HELP = "Collect well-known personal files (ssh, gpg, rclone, ...) found on this machine into ~/dotfiles and record them in the user mapper."


def _fail(message: str) -> Never:
    typer.echo(typer.style("Error: ", fg=typer.colors.RED) + message)
    raise typer.Exit(code=1)


def _describe_verdict(verdict: "CollectVerdict") -> str:
    match verdict:
        case "collect":
            return "will move into ~/dotfiles and link back"
        case "linked":
            return "already linked to the managed path; will record"
        case "stored":
            return "only the managed copy exists; will record, then sync down"
        case "recorded":
            return "already in your mapper"
        case "other_os":
            return "for another OS"
        case "absent":
            return "not on this machine"
        case "unreadable":
            return "skipped: permission denied"
        case "own_link":
            return "skipped: links somewhere you manage yourself"
        case "not_a_directory":
            return "skipped: expected a directory"
        case "managed_path_exists":
            return "skipped: original and managed copy both exist"
        case "original_mapped":
            return "skipped: original overlaps a path your mappers already manage"
        case "managed_path_mapped":
            return "skipped: managed path overlaps one your mappers already use"
        case "user_group":
            return "skipped: your mapper has its own group with this name"
        case _:
            assert_never(verdict)


def _choose_groups(plans: "list[CollectEntryPlan]", actionable_groups: list[str], which: str | None) -> list[str]:
    if which is not None:
        chosen_groups = actionable_groups if which.strip() == "all" else [item.strip() for item in which.split(",")]
        invalid_groups = [group for group in chosen_groups if group not in actionable_groups]
        if len(invalid_groups) > 0:
            _fail(f"""Not collectable on this machine: {", ".join(repr(group) for group in invalid_groups)}. Collectable: {", ".join(actionable_groups) or "none"}""")
        return chosen_groups
    import yaml

    from stackops.utils.options_utils.tv_options import choose_from_dict_with_preview

    previews = {
        group: yaml.safe_dump(
            {plan.name: {"verdict": _describe_verdict(plan.verdict), **plan.entry} for plan in plans if plan.group == group and plan.verdict != "other_os"},
            sort_keys=False,
        )
        for group in actionable_groups
    }
    return choose_from_dict_with_preview(previews, extension="yaml", multi=True, preview_size_percent=65.0)


def collect_dotfiles(
    which: Annotated[
        str | None,
        typer.Option(
            "--which",
            "-w",
            help="Groups of well-known files to collect, comma-separated, e.g. ssh,gpg,rclone (the Group column of the printed plan lists them), or 'all' for every group collectable on this machine. Omit to pick interactively.",
        ),
    ] = None,
) -> None:
    import platform

    from rich.console import Console
    from rich.table import Table

    from stackops.profile.create_links import ConfigMapper, apply_mapper, normalize_os_name, to_config_mapper
    from stackops.profile.dotfiles_collect_plan import ACTIONABLE_VERDICTS, plan_collect, select_entries_to_record
    from stackops.profile.dotfiles_mapper import (
        DEFAULT_DOTFILE_MAPPER_HEADER,
        LIBRARY_MAPPER_PATH,
        USER_EXAMPLE_MAPPER_PATH,
        USER_MAPPER_PATH,
        dump_dotfiles_mapper,
        load_dotfiles_mapper,
        write_dotfiles_mapper,
    )

    user_mapper = load_dotfiles_mapper(USER_MAPPER_PATH) if USER_MAPPER_PATH.exists() else {}
    current_os = normalize_os_name(platform.system())
    plans = plan_collect(
        catalog=load_dotfiles_mapper(USER_EXAMPLE_MAPPER_PATH),
        user_mapper=user_mapper,
        library_mapper=load_dotfiles_mapper(LIBRARY_MAPPER_PATH),
        current_os=current_os,
    )
    console = Console()
    table = Table(title="🧺 Dotfile collection plan", caption="Entries for other operating systems or absent from this machine are not listed.")
    for column_name in ("Group", "Entry", "Original", "Managed", "Verdict"):
        table.add_column(column_name, overflow="fold")
    for plan in plans:
        if current_os in plan.entry["os"] and plan.verdict != "absent":
            table.add_row(plan.group, plan.name, str(plan.original_path), str(plan.managed_path), _describe_verdict(plan.verdict))
    console.print(table)

    actionable_groups = list(dict.fromkeys(plan.group for plan in plans if plan.verdict in ACTIONABLE_VERDICTS))
    if len(actionable_groups) == 0 and (which is None or which.strip() == "all"):
        console.print("Nothing to collect: every well-known file on this machine is already recorded, absent, or managed your own way.")
        return
    chosen_groups = _choose_groups(plans, actionable_groups, which)
    if len(chosen_groups) == 0:
        _fail("No groups selected.")

    chosen_plans = [plan for plan in plans if plan.group in chosen_groups]
    collect_mapper: dict[str, list[ConfigMapper]] = {}
    for plan in chosen_plans:
        if plan.verdict == "collect":
            collect_mapper.setdefault(plan.group, []).append(to_config_mapper(file_name=plan.name, entry=plan.entry))
    operation_records = apply_mapper(mapper_data=collect_mapper, on_conflict="throw-error", method="symlink", direction="up") if len(collect_mapper) > 0 else []
    failed_entries = {(record["program"], record["file_key"]) for record in operation_records if record["action"] == "error"}
    succeeded_entries = {
        (plan.group, plan.name)
        for plan in chosen_plans
        if plan.verdict in ("linked", "stored") or (plan.verdict == "collect" and (plan.group, plan.name) not in failed_entries)
    }
    additions = select_entries_to_record(plans=chosen_plans, succeeded=succeeded_entries)
    if len(additions) > 0:
        merged_mapper = {group: dict(section) for group, section in user_mapper.items()}
        for group, section in additions.items():
            merged_mapper[group] = {**merged_mapper.get(group, {}), **section}
        USER_MAPPER_PATH.parent.mkdir(parents=True, exist_ok=True)
        write_dotfiles_mapper(path=USER_MAPPER_PATH, mapper=merged_mapper, header=DEFAULT_DOTFILE_MAPPER_HEADER)
        console.print(f"📝 Recorded in [cyan]{USER_MAPPER_PATH}[/cyan]:\n{dump_dotfiles_mapper(mapper=additions, header='')}")
    stored_groups = list(dict.fromkeys(plan.group for plan in chosen_plans if plan.verdict == "stored"))
    if len(stored_groups) > 0:
        console.print(f"""🔗 Link the recorded managed copies here with: devops config dotfiles sync down --source user --which {",".join(stored_groups)}""")
    if len(failed_entries) > 0:
        _fail(f"""Not recorded because collection failed: {", ".join(f"{group}.{name}" for group, name in sorted(failed_entries))}""")
