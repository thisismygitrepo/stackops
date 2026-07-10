from collections.abc import Mapping
from typing import Final

from stackops.scripts.python.helpers.helpers_agents.agents_iter_models import HerdrSnapshot, HerdrStatus, HerdrTab, HerdrWorkspace, TabId
from stackops.scripts.python.helpers.helpers_agents.agents_iter_records import IterationHandoff, current_herdr_session


_MUTATION_VETO_STATUSES: Final[frozenset[HerdrStatus]] = frozenset(("blocked", "unknown", "working"))


def mutation_veto_tab_ids(*, snapshot: HerdrSnapshot, workspace: HerdrWorkspace, tabs: tuple[HerdrTab, ...]) -> set[TabId]:
    tab_ids = {tab.tab_id for tab in tabs}
    active_ids = {tab.tab_id for tab in tabs if tab.agent_status in _MUTATION_VETO_STATUSES}
    active_ids.update(
        pane.tab_id
        for pane in snapshot.panes
        if pane.workspace_id == workspace.workspace_id and pane.tab_id in tab_ids and pane.agent_status in _MUTATION_VETO_STATUSES
    )
    active_ids.update(
        agent.tab_id
        for agent in snapshot.agents
        if agent.workspace_id == workspace.workspace_id and agent.tab_id in tab_ids and agent.agent_status in _MUTATION_VETO_STATUSES
    )
    return active_ids


def inventory_is_incomplete(*, snapshot: HerdrSnapshot, workspace: HerdrWorkspace, tabs: tuple[HerdrTab, ...], numbered: Mapping[TabId, int]) -> bool:
    tab_ids = {tab.tab_id for tab in tabs}
    panes = tuple(pane for pane in snapshot.panes if pane.workspace_id == workspace.workspace_id)
    agents = tuple(agent for agent in snapshot.agents if agent.workspace_id == workspace.workspace_id)
    if workspace.tab_count != len(tabs) or workspace.pane_count != len(panes) or workspace.active_tab_id not in tab_ids:
        return True
    if any(pane.tab_id not in tab_ids for pane in panes) or any(agent.tab_id not in tab_ids for agent in agents):
        return True
    for tab in tabs:
        attached_panes = tuple(pane for pane in panes if pane.tab_id == tab.tab_id)
        if tab.pane_count != 1 or len(attached_panes) != 1:
            return True
        attached_agents = tuple(agent for agent in agents if agent.tab_id == tab.tab_id)
        if tab.tab_id not in numbered:
            continue
        if len(attached_agents) != 1:
            return True
        agent = attached_agents[0]
        pane = attached_panes[0]
        if agent.name != tab.label or agent.pane_id != pane.pane_id or agent.terminal_id != pane.terminal_id:
            return True
    return False


def handoff_matches_snapshot(
    *, snapshot: HerdrSnapshot, workspace: HerdrWorkspace, source_tab: HerdrTab, source_iteration: int, handoff: IterationHandoff | None
) -> bool:
    if handoff is None:
        return False
    if (
        handoff.herdr_session != current_herdr_session()
        or handoff.workspace_id != workspace.workspace_id
        or handoff.source_iteration != source_iteration
        or handoff.source_tab_id != source_tab.tab_id
        or handoff.successor_iteration != source_iteration + 1
    ):
        return False
    successor_label = f"{workspace.label}-{handoff.successor_iteration:03d}"
    successor_tabs = tuple(
        tab
        for tab in snapshot.tabs
        if tab.workspace_id == workspace.workspace_id and tab.tab_id == handoff.successor_tab_id and tab.label == successor_label
    )
    successor_agents = tuple(
        agent
        for agent in snapshot.agents
        if agent.workspace_id == workspace.workspace_id
        and agent.tab_id == handoff.successor_tab_id
        and agent.pane_id == handoff.successor_pane_id
        and agent.terminal_id == handoff.successor_terminal_id
        and agent.name == handoff.successor_agent_name
        and agent.revision >= handoff.accepted_revision
    )
    return len(successor_tabs) == 1 and len(successor_agents) == 1 and handoff.successor_agent_name == successor_label
