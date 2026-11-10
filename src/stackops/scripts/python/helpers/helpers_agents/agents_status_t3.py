from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
import json
from typing import cast

from stackops.scripts.python.helpers.helpers_agents.agents_status_assessment import assess_status, describe_activity
from stackops.scripts.python.helpers.helpers_agents.agents_status_filters import selected_agent
from stackops.scripts.python.helpers.helpers_agents.agents_status_models import (
    AgentSnapshot,
    HistoryEvidence,
    JsonObject,
    MessageRecord,
    ProcessEvidence,
    StatusOptions,
    StatusSnapshot,
)
from stackops.scripts.python.helpers.helpers_agents.agents_status_tuios import text_field
from stackops.scripts.python.helpers.helpers_agents.agents_t3_mcp import (
    T3McpSession,
    call_t3_tool,
    open_t3_mcp_session,
    require_t3_object,
    require_t3_objects,
    require_t3_text,
)
from stackops.scripts.python.helpers.helpers_agents.constants import T3_MAX_CHARS_PER_ITEM, T3_SERVER_URL, T3_STATUS_PAGE_LIMIT


def _cursor_pages(*, session: T3McpSession, name: str, arguments: JsonObject, key: str) -> list[JsonObject]:
    rows: list[JsonObject] = []
    cursor: object = None
    while True:
        page = call_t3_tool(session=session, name=name, arguments=arguments if cursor is None else {**arguments, "cursor": cursor})
        rows.extend(require_t3_objects(page, key, name))
        cursor = page.get("nextCursor")
        if cursor is None:
            return rows


def _read_thread(*, session: T3McpSession, thread_id: str, options: StatusOptions) -> tuple[JsonObject, list[JsonObject]]:
    items: list[JsonObject] = []
    max_chars = min(options.text_limit, T3_MAX_CHARS_PER_ITEM) if options.text_limit else T3_MAX_CHARS_PER_ITEM
    arguments: JsonObject = {"threadId": thread_id, "view": "messages", "limit": 1 if options.history == "none" else T3_STATUS_PAGE_LIMIT, "maxCharsPerItem": max_chars}
    while True:
        page = call_t3_tool(session=session, name="t3_thread_read", arguments=arguments)
        thread = require_t3_object(page.get("thread"), "thread read")
        if options.history == "none":
            return thread, []
        items.extend(require_t3_objects(page, "items", "thread read"))
        position = page.get("nextPosition")
        if page.get("hasMore") is not True or position is None:
            return thread, items
        arguments = {**arguments, "afterPosition": position}


def _history(*, thread_id: str, items: list[JsonObject], options: StatusOptions) -> HistoryEvidence:
    if options.history == "none":
        return HistoryEvidence(messages=(), latest_reply="", latest_reply_at="", sources=(), coverage="disabled", limitations=(), omitted_messages=0)
    messages: list[MessageRecord] = []
    replies: list[tuple[str, str]] = []
    truncated = False
    for item in items:
        text = text_field(item, ("text",))
        if item.get("textTruncated") is True:
            truncated = True
            text += " [truncated]"
        timestamp = text_field(item, ("updatedAt", "createdAt"))
        match item.get("type"):
            case "user_message":
                source = f"""t3:thread:{thread_id}:position:{item.get('position')}"""
                messages.append(MessageRecord(timestamp=timestamp, text=text, source=source, kind="user", line=None))
            case "assistant_message":
                replies.append((timestamp, text))
            case _:
                pass
    omitted = max(0, len(messages) - options.message_limit) if options.message_limit else 0
    limitations = ["T3 Code's messages view holds user and assistant messages and plans; tool activity is not included."]
    if omitted:
        messages = messages[-options.message_limit:]
        limitations.append(f"""{omitted} older messages omitted by --messages.""")
    if truncated:
        limitations.append("Some message text was cut by --text-limit.")
    latest_reply_at, latest_reply = replies[-1] if replies else ("", "")
    return HistoryEvidence(
        messages=tuple(messages), latest_reply=latest_reply, latest_reply_at=latest_reply_at, sources=(f"""t3:thread:{thread_id}""",),
        coverage="complete", limitations=tuple(limitations), omitted_messages=omitted,
    )


def _inspect_thread(*, session: T3McpSession, options: StatusOptions, summary: JsonObject, projects: dict[str, JsonObject], drivers: dict[str, str]) -> AgentSnapshot:
    thread_id = require_t3_text(summary, "threadId", "thread")
    thread, items = _read_thread(session=session, thread_id=thread_id, options=options)
    history = _history(thread_id=thread_id, items=items, options=options)
    prompt: JsonObject = {}
    pending_count = thread.get("pendingRequestCount")
    if isinstance(pending_count, int) and pending_count > 0:
        listed = call_t3_tool(session=session, name="t3_pending_request", arguments={"action": "list", "threadId": thread_id})
        listed_ids = listed.get("requestIds")
        request_ids = [value for value in cast(list[object], listed_ids) if isinstance(value, str)] if isinstance(listed_ids, list) else []
        requests = [call_t3_tool(session=session, name="t3_pending_request", arguments={"action": "read", "threadId": thread_id, "requestId": request_id}) for request_id in request_ids]
        message = json.dumps(requests, ensure_ascii=False) if requests else f"""T3 Code reports {pending_count} pending requests."""
        if options.text_limit and len(message) > options.text_limit:
            message = message[:options.text_limit] + " [truncated]"
        prompt = {"found": True, "source": f"""t3:pending-request:{thread_id}""", "message": message}
    reported = text_field(thread, ("status",))
    mapped = {
        "running": "working", "preparing": "working", "queued": "working", "starting": "working", "waiting": "needs_input",
        "idle": "idle", "completed": "completed", "interrupted": "idle", "cancelled": "idle", "rolled_back": "idle", "failed": "failed",
    }.get(reported, "")
    state: JsonObject = {"state": mapped, "source": "T3 Code thread status"}
    if reported in {"interrupted", "cancelled", "rolled_back"}:
        state["message"] = f"""T3 Code reports the latest run {reported}."""
    instance = text_field(thread, ("providerInstanceId",))
    driver = drivers.get(instance, instance)
    harness = {"claudeAgent": "claude-code", "cursor": "cursor-agent", "antigravity": "agy"}.get(driver, driver) or "unknown"
    project_id = text_field(thread, ("projectId",))
    project = projects.get(project_id, {})
    cwd = text_field(thread, ("worktreePath",)) or text_field(project, ("workspaceRoot",))
    process = ProcessEvidence(
        pid=None, live=None, harness=harness, cwd=cwd, command="", session_id=thread_id, transcript_paths=(),
        limitations=("T3 Code runs providers inside its server; thread status is reported by T3 Code, not matched to a local process.",),
    )
    status, task_status, evidence, conflicts = assess_status(state=state, prompt=prompt, process=process, detector={}, backend="t3")
    task, activity = describe_activity(state=state, history=history, events=[], text_limit=options.text_limit)
    evidence.append(f"""T3 Code provider {instance or 'unknown'}, model {text_field(thread, ('model',)) or 'unknown'}, {text_field(thread, ('runtimeMode',)) or 'mode unknown'}; open {text_field(thread, ('link',)) or T3_SERVER_URL}.""")
    title = text_field(thread, ("title",))
    return AgentSnapshot(
        session=text_field(project, ("title",)) or project_id, session_id=project_id, workspace=None, workspace_name=text_field(thread, ("branch",)),
        workspace_id="", tab_id="", tab_name="", window_id=thread_id, window_name=title, agent_session_name=title,
        harness=harness, cwd=cwd, process=process, status=status, task_status=task_status, reported_state=reported, task=task,
        latest_activity=activity, history=history, prompt=prompt, capture="", events=(), evidence=tuple(evidence),
        limitations=tuple(dict.fromkeys((*process.limitations, *history.limitations, *conflicts))), btw=(),
    )


def collect_t3_status(options: StatusOptions) -> StatusSnapshot:
    started_at = datetime.now(UTC).isoformat()
    with open_t3_mcp_session(access="read-only") as session:
        capabilities = call_t3_tool(session=session, name="orchestrator_capabilities", arguments={})
        drivers = {
            require_t3_text(provider, "providerInstanceId", "provider"): require_t3_text(provider, "driverKind", "provider")
            for provider in require_t3_objects(capabilities, "providers", "capabilities")
        }
        projects = {
            require_t3_text(project, "id", "project"): project
            for project in _cursor_pages(session=session, name="t3_project_list", arguments={"limit": T3_STATUS_PAGE_LIMIT}, key="projects")
        }
        listed = _cursor_pages(session=session, name="t3_thread_list", arguments={"allProjects": True, "settled": False, "limit": T3_STATUS_PAGE_LIMIT}, key="threads")
        unique = list({require_t3_text(thread, "threadId", "thread"): thread for thread in listed}.values())
        threads = [thread for thread in unique if not text_field(thread, ("parentThreadId",))]
        settled_total = call_t3_tool(session=session, name="t3_thread_list", arguments={"allProjects": True, "settled": True, "limit": 1}).get("total")
        with ThreadPoolExecutor(max_workers=options.workers) as executor:
            agents = list(executor.map(
                lambda summary: _inspect_thread(session=session, options=options, summary=summary, projects=projects, drivers=drivers), threads,
            ))
    selected = tuple(agent for agent in agents if selected_agent(agent=agent, options=options))
    thread_counts = Counter(agent.session_id for agent in agents)
    coverage: JsonObject = {
        "projects": len(projects), "threads_discovered": len(threads), "threads_inspected": len(agents),
        "settled_threads_skipped": settled_total if isinstance(settled_total, int) else "unknown",
        "subagent_threads_skipped": len(unique) - len(threads),
        "sessions": [{"name": text_field(project, ("title",)), "id": project_id, "window_count": thread_counts[project_id]} for project_id, project in projects.items()],
        "agents_found": len(agents), "agents_shown": len(selected),
        "status_counts": dict(Counter(agent.status for agent in selected)),
        "task_status_counts": dict(Counter(agent.task_status for agent in selected)),
        "message_limit": options.message_limit, "text_limit": options.text_limit,
        "scope": f"""Local T3 Code server at {T3_SERVER_URL}; unsettled top-level threads in every project. Settled, archived and subagent threads are skipped; there are no layouts, tabs or panes.""",
    }
    return StatusSnapshot(
        backend="t3", started_at=started_at, observed_at=datetime.now(UTC).isoformat(), server=T3_SERVER_URL,
        agents=selected, coverage=coverage, limitations=(),
    )
