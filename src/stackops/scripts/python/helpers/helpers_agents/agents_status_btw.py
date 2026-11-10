from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import time
from typing import cast

from stackops.scripts.python.helpers.helpers_agents.agents_status_models import AgentSnapshot, BtwAnswer, BtwTopic, JsonObject, StatusSnapshot
from stackops.scripts.python.helpers.helpers_agents.agents_t3_mcp import (
    T3McpSession,
    call_t3_tool,
    open_t3_mcp_session,
    require_t3_objects,
    require_t3_text,
)
from stackops.scripts.python.helpers.helpers_agents.constants import (
    AGENTS_STATUS_BTW_ENV_PREFIXES,
    AGENTS_STATUS_BTW_QUESTIONS,
    T3_MAX_CHARS_PER_ITEM,
    T3_STATUS_PAGE_LIMIT,
    T3_TITLE_MAX_CHARS,
    T3_WAIT_SLICE_MS,
)


def _home_override(*, agent: AgentSnapshot, marker: str, variable: str, default: Path) -> dict[str, str]:
    homes = {parent.parent for path in agent.process.transcript_paths for parent in path.parents if parent.name == marker}
    if len(homes) != 1:
        return {}
    home = next(iter(homes))
    return {} if home == Path(os.environ.get(variable, str(default))).expanduser() else {variable: str(home)}


def _run_fork(*, command: list[str], cwd: str, question: str, timeout: float, overrides: dict[str, str]) -> tuple[str, str]:
    environment = {key: value for key, value in os.environ.items() if not key.startswith(AGENTS_STATUS_BTW_ENV_PREFIXES)} | overrides
    try:
        completed = subprocess.run(command, input=question, capture_output=True, text=True, cwd=cwd or None, env=environment, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        return "", f"""{command[0]}: {error}"""
    if completed.returncode != 0:
        return "", f"""{command[0]} exited {completed.returncode}: {(completed.stderr.strip() or completed.stdout.strip())[-500:]}"""
    return completed.stdout, ""


def _ask_claude(*, agent: AgentSnapshot, question: str, timeout: float) -> tuple[str, str]:
    output, error = _run_fork(
        command=[
            "claude", "-p", "--resume", agent.process.session_id, "--fork-session", "--no-session-persistence",
            "--tools", "", "--strict-mcp-config", "--output-format", "json",
        ],
        cwd=agent.process.cwd or agent.cwd, question=question, timeout=timeout,
        overrides=_home_override(agent=agent, marker="projects", variable="CLAUDE_CONFIG_DIR", default=Path.home() / ".claude"),
    )
    if error:
        return "", error
    try:
        result: object = json.loads(output)
    except json.JSONDecodeError as invalid:
        return "", f"""claude returned invalid JSON: {invalid}"""
    if not isinstance(result, dict):
        return "", "claude returned a non-object result."
    payload = cast(JsonObject, result)
    answer = payload.get("result")
    if payload.get("is_error") is True or not isinstance(answer, str):
        return "", f"""claude side question failed: {json.dumps(payload, default=str)[:500]}"""
    return answer.strip(), ""


def _ask_codex(*, agent: AgentSnapshot, question: str, timeout: float) -> tuple[str, str]:
    output, error = _run_fork(
        command=[
            "codex", "exec", "fork", "--ephemeral", "--skip-git-repo-check", "--json",
            "-c", 'sandbox_mode="read-only"', "-c", 'approval_policy="never"', agent.process.session_id, "-",
        ],
        cwd=agent.process.cwd or agent.cwd, question=question, timeout=timeout,
        overrides=_home_override(agent=agent, marker="sessions", variable="CODEX_HOME", default=Path.home() / ".codex"),
    )
    if error:
        return "", error
    replies: list[str] = []
    for line in output.splitlines():
        try:
            event: object = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = cast(JsonObject, event).get("item") if isinstance(event, dict) and cast(JsonObject, event).get("type") == "item.completed" else None
        if isinstance(item, dict) and cast(JsonObject, item).get("type") == "agent_message" and isinstance(text := cast(JsonObject, item).get("text"), str):
            replies.append(text)
    return (replies[-1].strip(), "") if replies else ("", "codex fork produced no agent message.")


def _ask_t3(*, session: T3McpSession, agent: AgentSnapshot, topic: BtwTopic, question: str, timeout: float) -> tuple[str, str]:
    title = f"""btw {topic}: {agent.window_name or agent.window_id}"""[:T3_TITLE_MAX_CHARS]
    forked = call_t3_tool(session=session, name="t3_thread_transfer", arguments={"action": "fork", "threadId": agent.window_id, "title": title})
    fork_id = require_t3_text(forked, "targetThreadId", "fork")
    if fork_id == agent.window_id:
        raise RuntimeError("T3 Code fork returned the source thread ID; the side question was not sent.")
    try:
        run_id = require_t3_text(call_t3_tool(session=session, name="t3_thread_send", arguments={"threadId": fork_id, "message": question, "mode": "queue"}), "runId", "send")
        deadline = time.monotonic() + timeout
        while True:
            remaining_ms = int((deadline - time.monotonic()) * 1000)
            if remaining_ms <= 0:
                call_t3_tool(session=session, name="t3_thread_interrupt", arguments={"threadId": fork_id, "runId": run_id})
                return "", f"""The T3 Code fork did not answer within {timeout:.0f} seconds and was interrupted."""
            waited = call_t3_tool(session=session, name="t3_thread_wait", arguments={"threadId": fork_id, "runId": run_id, "timeoutMs": min(T3_WAIT_SLICE_MS, remaining_ms)})
            if waited.get("timedOut") is not True:
                break
        if waited.get("status") != "completed":
            return "", f"""The T3 Code fork run ended {waited.get('status')}."""
        replies: list[str] = []
        arguments: JsonObject = {"threadId": fork_id, "view": "messages", "limit": T3_STATUS_PAGE_LIMIT, "maxCharsPerItem": T3_MAX_CHARS_PER_ITEM}
        while True:
            page = call_t3_tool(session=session, name="t3_thread_read", arguments=arguments)
            replies.extend(
                text for item in require_t3_objects(page, "items", "fork read")
                if item.get("type") == "assistant_message" and item.get("runId") == run_id and isinstance(text := item.get("text"), str)
            )
            position = page.get("nextPosition")
            if page.get("hasMore") is not True or position is None:
                break
            arguments = {**arguments, "afterPosition": position}
        return (replies[-1].strip(), "") if replies else ("", "The T3 Code fork finished without an assistant message.")
    finally:
        call_t3_tool(session=session, name="t3_thread_organize", arguments={"threadId": fork_id, "action": "archive"})


def _answer(*, snapshot: StatusSnapshot, agent: AgentSnapshot, session: T3McpSession | None, topic: BtwTopic, question: str, timeout: float, text_limit: int) -> BtwAnswer:
    answer, error = "", ""
    try:
        if session is not None:
            route = "T3 Code fork of the latest completed run, archived afterwards"
            answer, error = _ask_t3(session=session, agent=agent, topic=topic, question=question, timeout=timeout)
        elif agent.harness == "claude-code" and agent.process.session_id:
            route = "claude --resume --fork-session --no-session-persistence, no tools"
            answer, error = _ask_claude(agent=agent, question=question, timeout=timeout)
        elif agent.harness == "codex" and agent.process.session_id:
            route = "codex exec fork --ephemeral, read-only sandbox"
            answer, error = _ask_codex(agent=agent, question=question, timeout=timeout)
        else:
            route = "unavailable"
            error = f"""No side-question route for {agent.harness or 'an unknown harness'} on {snapshot.backend}: it needs a linked Claude Code or Codex conversation ID."""
    except (OSError, RuntimeError, ValueError) as failure:
        route = "T3 Code fork" if session is not None else "fork"
        error = str(failure)
    if text_limit and len(answer) > text_limit:
        answer = answer[:text_limit] + " [truncated]"
    return BtwAnswer(topic=topic, question=question, answer=answer, route=route, error=error)


def ask_btw(*, snapshot: StatusSnapshot, workers: int, timeout: float, text_limit: int) -> StatusSnapshot:
    pairs = [(agent, topic, question) for agent in snapshot.agents for topic, question in AGENTS_STATUS_BTW_QUESTIONS]
    with open_t3_mcp_session(access="full-access") if snapshot.backend == "t3" and pairs else nullcontext() as session:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            answers = list(executor.map(
                lambda pair: _answer(snapshot=snapshot, agent=pair[0], session=session, topic=pair[1], question=pair[2], timeout=timeout, text_limit=text_limit),
                pairs,
            ))
    per_agent = len(AGENTS_STATUS_BTW_QUESTIONS)
    agents = tuple(replace(agent, btw=tuple(answers[index * per_agent:(index + 1) * per_agent])) for index, agent in enumerate(snapshot.agents))
    return replace(snapshot, agents=agents)
