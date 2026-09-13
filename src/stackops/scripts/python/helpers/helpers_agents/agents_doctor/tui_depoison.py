import asyncio
from pathlib import Path

from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Button, Footer, Header, Input, Static, TextArea

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_apply import apply_cleanup_plan
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_interactive import CleanupSelection
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_models import CleanupPlan, CleanupScope
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.command import resolve_resource_focuses
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.models import HookInventory
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorContext
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.registry import DOCTOR_AGENT_DEFINITIONS, resolve_doctor_definitions
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.scanning import create_doctor_context
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.tui_cleanup import build_selected_cleanup_plan, inspect_cleanup_agent, selected_cleanup_inventory
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.tui_cleanup_browser import CleanupBrowser, CleanupResourceTable
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.tui_cleanup_review import CleanupReview


class DepoisonApp(App[int]):
    TITLE = "Agent depoison"
    BINDINGS = [
        Binding("f5", "refresh_inventory", "Refresh"),
        Binding("ctrl+f", "search", "Search", priority=True),
        Binding("ctrl+r", "review", "Review reset", priority=True),
        Binding("ctrl+q", "close", "Quit", priority=True),
        Binding("ctrl+c", "close", show=False, priority=True),
    ]
    CSS = """
    DepoisonApp Screen { padding: 0 1; }
    #cleanup-actions { height: 3; }
    #cleanup-count { width: 1fr; content-align: left middle; }
    #cleanup-status { height: auto; max-height: 3; }
    """

    def __init__(self, *, selection: CleanupSelection) -> None:
        super().__init__()
        self.cleanup_selection = selection
        self.sub_title = selection.directory
        self.cleanup_context: DoctorContext | None = None
        self.cleanup_plan: CleanupPlan | None = None
        self.cleanup_busy = False
        self.cleanup_applying = False
        self.cleanup_scanned = False
        self.cleanup_exit_code = 0

    def compose(self) -> ComposeResult:
        yield Header()
        yield CleanupBrowser(selection=self.cleanup_selection)
        with Horizontal(id="cleanup-actions"):
            yield Static("Select resources with Space or Enter.", id="cleanup-count")
            yield Button("Refresh", id="cleanup-refresh")
            yield Button("Review reset…", variant="primary", id="cleanup-review", disabled=True)
        yield Static("Preparing inspection…", id="cleanup-status", markup=False)
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(CleanupResourceTable).focus()
        self.call_after_refresh(self.action_refresh_inventory)

    def action_search(self) -> None:
        if not self.cleanup_busy:
            search = self.query_one("#cleanup-search", Input)
            search.focus()
            search.action_select_all()

    @on(Button.Pressed, "#cleanup-refresh")
    def action_refresh_inventory(self) -> None:
        if self.cleanup_busy or isinstance(self.screen, CleanupReview):
            return
        self.cleanup_plan = None
        self.cleanup_scanned = False
        self.set_cleanup_busy(True)
        self.scan_inventory()

    @work
    async def scan_inventory(self) -> None:
        try:
            self.cleanup_context = await asyncio.to_thread(create_doctor_context, working_directory=Path(self.cleanup_selection.directory))
            inventories: list[HookInventory] = []
            definitions = sorted(DOCTOR_AGENT_DEFINITIONS, key=lambda item: item.agent != self.cleanup_selection.agent)
            for index, definition in enumerate(definitions, start=1):
                self.query_one("#cleanup-status", Static).update(f"""Inspecting {definition.display_name} · {index}/{len(definitions)}…""")
                inventories.append(await asyncio.to_thread(inspect_cleanup_agent, agent=definition.agent, context=self.cleanup_context))
            inventory = HookInventory(
                entries=tuple(dict.fromkeys(entry for item in inventories for entry in item.entries)),
                diagnostics=tuple(dict.fromkeys(diagnostic for item in inventories for diagnostic in item.diagnostics)),
            )
            self.query_one(CleanupBrowser).load_inventory(inventory)
            self.cleanup_scanned = True
            self.cleanup_exit_code = 0
            errors = sum(item.severity == "error" for item in inventory.diagnostics)
            self.query_one("#cleanup-status", Static).update(
                f"""{len(inventory.entries)} resources · {errors} inspection errors. Filters are live; linked reset actions are selected together.""",
            )
        except (OSError, ValueError) as error:
            self.cleanup_exit_code = 2
            self.query_one("#cleanup-status", Static).update(Text(f"""Inspection failed: {error}""", style="red"))
        finally:
            self.set_cleanup_busy(False)
            self.query_one(CleanupResourceTable).focus()

    @on(CleanupBrowser.Changed)
    def update_cleanup_selection(self) -> None:
        browser = self.query_one(CleanupBrowser)
        selected = selected_cleanup_inventory(inventory=browser.cleanup_inventory, selected=browser.cleanup_selected)
        hidden = sum(index not in browser.cleanup_visible for index, entry in enumerate(browser.cleanup_inventory.entries) if entry in selected.entries)
        self.query_one("#cleanup-count", Static).update(f"""{len(selected.entries)} resources selected · {hidden} hidden by filters""")
        self.query_one("#cleanup-review", Button).disabled = self.cleanup_busy or not self.cleanup_scanned or not selected.entries

    def set_cleanup_busy(self, busy: bool) -> None:
        self.cleanup_busy = busy
        self.query_one(CleanupBrowser).disabled = busy
        self.query_one("#cleanup-refresh", Button).disabled = busy
        self.update_cleanup_selection()

    @on(Button.Pressed, "#cleanup-review")
    def action_review(self) -> None:
        if self.cleanup_busy or isinstance(self.screen, CleanupReview) or not self.cleanup_scanned:
            return
        browser = self.query_one(CleanupBrowser)
        inventory = selected_cleanup_inventory(inventory=browser.cleanup_inventory, selected=browser.cleanup_selected)
        if inventory.entries and self.cleanup_context is not None:
            self.set_cleanup_busy(True)
            self.query_one("#cleanup-status", Static).update("Rechecking selected resources and building file diffs…")
            self.review_cleanup(inventory, self.cleanup_context)

    @work
    async def review_cleanup(self, inventory: HookInventory, context: DoctorContext) -> None:
        try:
            self.cleanup_plan = await asyncio.to_thread(
                build_selected_cleanup_plan, inventory=inventory, context=context,
            )
            self.cleanup_exit_code = 1 if self.cleanup_plan.blockers else 0
            self.push_screen(CleanupReview(
                plan=self.cleanup_plan, backup_root=context.home_directory / ".local" / "state" / "stackops" / "depoison",
            ), self.reset_reviewed)
        except (OSError, ValueError) as error:
            self.cleanup_exit_code = 2
            self.set_cleanup_busy(False)
            self.query_one("#cleanup-status", Static).update(Text(str(error), style="red"))

    def reset_reviewed(self, confirmed: bool | None) -> None:
        if confirmed and self.cleanup_plan is not None and self.cleanup_context is not None:
            self.cleanup_applying = True
            self.query_one("#cleanup-status", Static).update("Saving originals and applying the reviewed reset…")
            self.apply_reviewed_cleanup(self.cleanup_plan, self.cleanup_context)
        else:
            self.set_cleanup_busy(False)
            self.query_one(CleanupResourceTable).focus()
            self.query_one("#cleanup-status", Static).update("Review closed. No changes applied.")

    @work
    async def apply_reviewed_cleanup(self, plan: CleanupPlan, context: DoctorContext) -> None:
        try:
            result = await asyncio.to_thread(
                apply_cleanup_plan, plan=plan, home_directory=context.home_directory,
                backup_root=context.home_directory / ".local" / "state" / "stackops" / "depoison",
            )
            self.cleanup_exit_code = 0
            self.cleanup_scanned = False
            browser = self.query_one(CleanupBrowser)
            browser.cleanup_selected.clear()
            browser.update_marks()
            browser.query_one("#cleanup-detail", TextArea).load_text(
                f"""Reset {len(result.changed_paths)} path(s).

Originals and restore manifest: {result.backup_directory}

Refresh to inspect the current configuration. Restart the agent to load it.""",
            )
            self.query_one("#cleanup-status", Static).update("Reset complete. Refresh before selecting another reset.")
        except (OSError, ValueError) as error:
            self.cleanup_exit_code = 2
            self.query_one("#cleanup-status", Static).update(Text(str(error), style="red"))
        finally:
            self.cleanup_plan = None
            self.cleanup_applying = False
            self.set_cleanup_busy(False)

    def action_close(self) -> None:
        if not self.cleanup_applying:
            self.exit(self.cleanup_exit_code)


def run_depoison_tui(*, agent: str, directory: str, scope: CleanupScope, resource: str, match: str | None) -> None:
    definitions = resolve_doctor_definitions(requested_agent=agent)
    selection = CleanupSelection(
        agent=definitions[0].agent if len(definitions) == 1 else "all", directory=directory,
        scope=scope, resource=",".join(resolve_resource_focuses(requested_resources=resource)), match=match,
    )
    raise SystemExit(DepoisonApp(selection=selection).run())
