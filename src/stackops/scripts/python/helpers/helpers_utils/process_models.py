from dataclasses import dataclass
from datetime import datetime
from typing import Literal, TypedDict, assert_never


type TextSearchField = Literal["command", "name", "username", "status"]
type IntegerSearchField = Literal["ports", "pid"]
type MinimumSearchField = Literal["memory", "cpu"]
type SearchField = TextSearchField | IntegerSearchField | MinimumSearchField


class ProcessInfo(TypedDict):
    command: str
    pid: int
    name: str
    username: str
    cpu_percent: float
    memory_usage_mb: float
    status: str
    create_time: datetime
    ports: list[int]


@dataclass(frozen=True, slots=True)
class TextProcessSelector:
    field: TextSearchField
    value: str


@dataclass(frozen=True, slots=True)
class IntegerProcessSelector:
    field: IntegerSearchField
    value: int


@dataclass(frozen=True, slots=True)
class MinimumProcessSelector:
    field: MinimumSearchField
    value: float


type ProcessSelector = TextProcessSelector | IntegerProcessSelector | MinimumProcessSelector


def build_process_selector(
    command: str | None,
    port: int | None,
    name: str | None,
    pid: int | None,
    username: str | None,
    status: str | None,
    memory: float | None,
    cpu: float | None,
) -> ProcessSelector | None:
    selectors: list[ProcessSelector] = []
    if command is not None:
        selectors.append(TextProcessSelector(field="command", value=command))
    if port is not None:
        selectors.append(IntegerProcessSelector(field="ports", value=port))
    if name is not None:
        selectors.append(TextProcessSelector(field="name", value=name))
    if pid is not None:
        selectors.append(IntegerProcessSelector(field="pid", value=pid))
    if username is not None:
        selectors.append(TextProcessSelector(field="username", value=username))
    if status is not None:
        selectors.append(TextProcessSelector(field="status", value=status))
    if memory is not None:
        selectors.append(MinimumProcessSelector(field="memory", value=memory))
    if cpu is not None:
        selectors.append(MinimumProcessSelector(field="cpu", value=cpu))
    if len(selectors) > 1:
        raise ValueError("Pass exactly one direct process selector.")
    if len(selectors) == 0:
        return None
    selector = selectors[0]
    if isinstance(selector, TextProcessSelector) and selector.value.strip() == "":
        raise ValueError("Direct process selectors cannot be empty.")
    return selector


def process_matches_selector(process: ProcessInfo, selector: ProcessSelector) -> bool:
    match selector:
        case TextProcessSelector():
            match selector.field:
                case "command":
                    return selector.value.casefold() in process["command"].casefold()
                case "name":
                    return process["name"] == selector.value
                case "username":
                    return process["username"] == selector.value
                case "status":
                    return process["status"] == selector.value
                case _ as unreachable:
                    assert_never(unreachable)
        case IntegerProcessSelector():
            match selector.field:
                case "ports":
                    return selector.value in process["ports"]
                case "pid":
                    return process["pid"] == selector.value
                case _ as unreachable:
                    assert_never(unreachable)
        case MinimumProcessSelector():
            match selector.field:
                case "memory":
                    return process["memory_usage_mb"] >= selector.value
                case "cpu":
                    return process["cpu_percent"] >= selector.value
                case _ as unreachable:
                    assert_never(unreachable)
        case _ as unreachable:
            assert_never(unreachable)
