from collections.abc import Callable
from dataclasses import dataclass
import sys
from types import ModuleType
from typing import cast

from click import Command, Context
import pytest
from _pytest.capture import CaptureFixture
from _pytest.monkeypatch import MonkeyPatch
import typer

import stackops.scripts.python.fire_jobs as target


type RouteImpl = Callable[["FakeFireJobArgs", object], None]


@dataclass(frozen=True)
class FakeFireJobArgs:
    path: str
    function: str | None
    ve: str
    frozen: bool
    cmd: bool
    interactive: bool
    debug: bool
    choose_function: bool
    loop: bool
    jupyter: bool
    marimo: bool
    submit_to_cloud: bool
    root_repo: bool
    remote: bool
    module: bool
    script: bool
    streamlit: bool
    environment: str
    holdDirectory: bool
    PathExport: bool
    git_pull: bool
    optimized: bool
    zellij_tab: str | None
    watch: bool


def _install_fire_job_modules(
    monkeypatch: MonkeyPatch,
    *,
    parsed_fire_args: object,
    route_impl: RouteImpl,
) -> None:
    args_module = ModuleType(
        "stackops.scripts.python.helpers.helpers_fire_command.fire_jobs_args_helper"
    )
    impl_module = ModuleType(
        "stackops.scripts.python.helpers.helpers_fire_command.fire_jobs_impl"
    )

    def parse_fire_args_from_context(ctx: Context) -> object:
        _ = ctx
        return parsed_fire_args

    def route(args: FakeFireJobArgs, fire_args: object) -> None:
        route_impl(args, fire_args)

    setattr(args_module, "FireJobArgs", FakeFireJobArgs)
    setattr(args_module, "parse_fire_args_from_context", parse_fire_args_from_context)
    setattr(impl_module, "route", route)
    monkeypatch.setitem(sys.modules, args_module.__name__, args_module)
    monkeypatch.setitem(sys.modules, impl_module.__name__, impl_module)


def _ctx() -> typer.Context:
    return cast(typer.Context, Context(Command("fire")))


def test_fire_routes_explicit_arguments(monkeypatch: MonkeyPatch) -> None:
    parsed_fire_args = object()
    seen_calls: list[tuple[FakeFireJobArgs, object]] = []

    def route_impl(args: FakeFireJobArgs, fire_args: object) -> None:
        seen_calls.append((args, fire_args))

    _install_fire_job_modules(
        monkeypatch,
        parsed_fire_args=parsed_fire_args,
        route_impl=route_impl,
    )

    target.fire(
        ctx=_ctx(),
        path="jobs.py",
        function="launch",
        frozen=True,
        ve=".venv",
        cmd=True,
        interactive=True,
        debug=True,
        choose_function=True,
        loop=True,
        jupyter=True,
        marimo=True,
        module=True,
        script=True,
        optimized=True,
        zellij_tab="jobs",
        submit_to_cloud=True,
        root_repo=True,
        remote=True,
        streamlit=True,
        environment="localhost",
        holdDirectory=True,
        PathExport=True,
        git_pull=True,
        watch=True,
    )

    assert seen_calls == [
        (
            FakeFireJobArgs(
                path="jobs.py",
                function="launch",
                ve=".venv",
                frozen=True,
                cmd=True,
                interactive=True,
                debug=True,
                choose_function=True,
                loop=True,
                jupyter=True,
                marimo=True,
                submit_to_cloud=True,
                root_repo=True,
                remote=True,
                module=True,
                script=True,
                streamlit=True,
                environment="localhost",
                holdDirectory=True,
                PathExport=True,
                git_pull=True,
                optimized=True,
                zellij_tab="jobs",
                watch=True,
            ),
            parsed_fire_args,
        )
    ]


def test_fire_prints_runtime_errors_and_exits(
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    def route_impl(args: FakeFireJobArgs, fire_args: object) -> None:
        _ = args
        _ = fire_args
        raise RuntimeError("boom")

    _install_fire_job_modules(
        monkeypatch,
        parsed_fire_args=object(),
        route_impl=route_impl,
    )

    with pytest.raises(SystemExit) as exc_info:
        target.fire(
            ctx=_ctx(),
            path=".",
            function=None,
            frozen=False,
            ve="",
            cmd=False,
            interactive=False,
            debug=False,
            choose_function=False,
            loop=False,
            jupyter=False,
            marimo=False,
            module=False,
            script=False,
            optimized=False,
            zellij_tab=None,
            submit_to_cloud=False,
            root_repo=False,
            remote=False,
            streamlit=False,
            environment="",
            holdDirectory=False,
            PathExport=False,
            git_pull=False,
            watch=False,
        )

    assert exc_info.value.code == 1
    assert "❌ fire_jobs Error: boom" in capsys.readouterr().err


def test_get_app_keeps_fire_context_settings() -> None:
    app = target.get_app()

    assert len(app.registered_commands) == 1
    command_info = app.registered_commands[0]
    assert command_info.context_settings == {
        "allow_extra_args": True,
        "allow_interspersed_args": False,
    }
