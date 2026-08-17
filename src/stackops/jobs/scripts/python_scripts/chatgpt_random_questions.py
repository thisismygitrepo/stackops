#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "playwright>=1.49.0",
#   "rich>=13.9.0",
#   "typer>=0.15.0",
# ]
# ///

import asyncio
import random
import re
import signal
import time
from pathlib import Path
from typing import Annotated

import typer
from playwright.async_api import Locator, Page, TimeoutError as PlaywrightTimeoutError, async_playwright
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text


DEFAULT_QUESTIONS = [
    "What is one practical way to organize my day better?",
    "Explain a useful idea from science in simple terms.",
    "Give me a short writing prompt.",
    "What is a good five-minute habit to build?",
    "Teach me one interesting historical fact.",
    "What is a simple recipe idea using common pantry ingredients?",
    "Give me a small Python exercise for practice.",
    "What is one way to improve focus while working?",
    "Explain a common misconception in technology.",
    "Suggest a quick mental math trick.",
]


app = typer.Typer(add_completion=False, help=("Send random local questions to ChatGPT through an existing logged-in Chrome/Chromium CDP session."))
console = Console()


class StopRequested(Exception):
    pass


async def find_composer(page: Page) -> Locator:
    candidates = [
        page.get_by_role("textbox", name=re.compile(r"(chat with chatgpt|message)", re.I)).last,
        page.locator('[contenteditable="true"]').last,
        page.locator("textarea").last,
    ]

    last_error: Exception | None = None
    for candidate in candidates:
        try:
            await candidate.wait_for(state="visible", timeout=10_000)
            return candidate
        except Exception as exc:  # Playwright has several timeout subclasses.
            last_error = exc

    login_visible = await page.get_by_role("button", name=re.compile(r"log in|sign in", re.I)).count()
    if login_visible:
        raise RuntimeError("ChatGPT appears to be logged out. Log in in the browser, then rerun.")

    raise RuntimeError(f"Could not find the ChatGPT message composer: {last_error}")


async def extract_last_assistant_message(page: Page) -> str:
    text = await page.evaluate(
        """
        () => {
          const normalize = (value) => (value || "").replace(/\\s+\\n/g, "\\n").trim();

          const roleMessages = Array.from(
            document.querySelectorAll('[data-message-author-role="assistant"]')
          )
            .map((node) => normalize(node.innerText || node.textContent))
            .filter(Boolean);
          if (roleMessages.length) return roleMessages.at(-1);

          const articles = Array.from(document.querySelectorAll("article"))
            .map((node) => normalize(node.innerText || node.textContent))
            .filter((value) => value && !/^you\\b/i.test(value));
          return articles.at(-1) || "";
        }
        """
    )
    return str(text or "").strip()


async def is_generating(page: Page) -> bool:
    return bool(
        await page.evaluate(
            """
            () => {
              const pattern = /stop (generating|answering|streaming)|stop response/i;
              return Array.from(document.querySelectorAll("button")).some((button) => {
                const label = [
                  button.innerText,
                  button.getAttribute("aria-label"),
                  button.getAttribute("title"),
                ].filter(Boolean).join(" ");
                return pattern.test(label);
              });
            }
            """
        )
    )


async def wait_for_response(page: Page, *, timeout_seconds: float, poll_seconds: float, stable_seconds: float) -> str:
    deadline = time.monotonic() + timeout_seconds
    last_text = ""
    stable_since = time.monotonic()

    while time.monotonic() < deadline:
        text = await extract_last_assistant_message(page)
        generating = await is_generating(page)

        if text and text != last_text:
            last_text = text
            stable_since = time.monotonic()
        elif text and not generating and time.monotonic() - stable_since >= stable_seconds:
            return text

        await asyncio.sleep(poll_seconds)

    if last_text:
        return last_text
    raise TimeoutError("Timed out waiting for a ChatGPT response.")


async def send_question(
    *,
    page: Page,
    question: str,
    chatgpt_url: str,
    pre_submit_wait_seconds: float,
    response_timeout_seconds: float,
    poll_seconds: float,
    stable_seconds: float,
) -> str:
    await page.goto(chatgpt_url, wait_until="domcontentloaded", timeout=60_000)
    await page.wait_for_load_state("domcontentloaded")
    await asyncio.sleep(pre_submit_wait_seconds)

    composer = await find_composer(page)
    await composer.click()
    await composer.fill(question)
    await composer.press("Enter")

    return await wait_for_response(page, timeout_seconds=response_timeout_seconds, poll_seconds=poll_seconds, stable_seconds=stable_seconds)


def load_questions(question_options: list[str] | None, questions_file: Path | None) -> list[str]:
    questions: list[str] = []

    if question_options:
        questions.extend(q.strip() for q in question_options if q.strip())

    if questions_file:
        if not questions_file.exists():
            raise typer.BadParameter(f"questions file does not exist: {questions_file}")
        file_questions = [
            line.strip() for line in questions_file.read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith("#")
        ]
        questions.extend(file_questions)

    return questions or list(DEFAULT_QUESTIONS)


def print_cycle(cycle: int, question: str, response: str) -> None:
    table = Table.grid(padding=(0, 1))
    table.add_column(style="bold cyan", no_wrap=True)
    table.add_column()
    table.add_row("Cycle", str(cycle))
    table.add_row("Question", question)
    table.add_row("Response", response)
    console.print(Panel(table, title="ChatGPT response", border_style="green"))


async def sleep_with_status(seconds: float, *, cycle: int) -> None:
    if seconds <= 0:
        return

    with Progress(
        SpinnerColumn(), TextColumn(f"Waiting {seconds:g}s before cycle {cycle + 1}"), TimeElapsedColumn(), transient=True, console=console
    ) as progress:
        task = progress.add_task("sleep", total=None)
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            progress.update(task)
            await asyncio.sleep(min(1.0, end - time.monotonic()))


async def run_loop(
    *,
    cdp_url: str,
    chatgpt_url: str,
    interval_seconds: float,
    cycles: int | None,
    questions: list[str],
    seed: int | None,
    pre_submit_wait_seconds: float,
    response_timeout_seconds: float,
    poll_seconds: float,
    stable_seconds: float,
    keep_tabs: bool,
    dry_run: bool,
) -> None:
    rng = random.Random(seed)

    if dry_run:
        question = rng.choice(questions)
        console.print(Panel(question, title="Dry run question", border_style="yellow"))
        return

    stop = asyncio.Event()

    def request_stop(*_: object) -> None:
        stop.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, request_stop)
        except NotImplementedError:
            pass

    async with async_playwright() as playwright:
        browser = await playwright.chromium.connect_over_cdp(cdp_url)
        if not browser.contexts:
            raise RuntimeError("Connected to CDP, but no browser contexts were available.")

        context = browser.contexts[0]
        cycle = 0

        try:
            while not stop.is_set():
                cycle += 1
                if cycles is not None and cycle > cycles:
                    break

                question = rng.choice(questions)
                page = await context.new_page()

                try:
                    console.print(f"[bold cyan]Cycle {cycle}[/]: opening {chatgpt_url}")
                    response = await send_question(
                        page=page,
                        question=question,
                        chatgpt_url=chatgpt_url,
                        pre_submit_wait_seconds=pre_submit_wait_seconds,
                        response_timeout_seconds=response_timeout_seconds,
                        poll_seconds=poll_seconds,
                        stable_seconds=stable_seconds,
                    )
                    print_cycle(cycle, question, response)
                except PlaywrightTimeoutError as exc:
                    console.print(Panel(str(exc), title=f"Cycle {cycle} timed out", border_style="red"))
                except Exception as exc:
                    console.print(Panel(str(exc), title=f"Cycle {cycle} failed", border_style="red"))
                finally:
                    if not keep_tabs:
                        await page.close()

                if cycles is not None and cycle >= cycles:
                    break

                await sleep_with_status(interval_seconds, cycle=cycle)
        finally:
            # The script attaches to an existing browser over CDP. Close per-cycle tabs,
            # but do not intentionally shut down the user's browser process on exit.
            pass


@app.command()
def main(
    cdp_url: Annotated[
        str, typer.Option("--cdp-url", help="Chrome DevTools Protocol endpoint for the already-running browser.")
    ] = "http://192.168.0.13:9999",
    chatgpt_url: Annotated[str, typer.Option("--chatgpt-url", help="ChatGPT URL to open in each new tab.")] = "https://chatgpt.com/",
    interval_minutes: Annotated[
        float, typer.Option("--interval-minutes", "-i", min=0.0, help="Minutes to wait between cycles. Default is 10 minutes.")
    ] = 10.0,
    cycles: Annotated[int | None, typer.Option("--cycles", "-n", min=1, help="Number of cycles to run. Omit for infinite repeat.")] = None,
    question: Annotated[
        list[str] | None, typer.Option("--question", "-q", help="Question to include in the random pool. Can be passed multiple times.")
    ] = None,
    questions_file: Annotated[
        Path | None,
        typer.Option(
            "--questions-file", "-f", exists=False, dir_okay=False, help="Newline-delimited question file. Empty lines and # comments are ignored."
        ),
    ] = None,
    seed: Annotated[int | None, typer.Option("--seed", help="Random seed for reproducible question selection.")] = None,
    pre_submit_wait_seconds: Annotated[
        float, typer.Option("--pre-submit-wait-seconds", min=0.0, help="Seconds to wait after opening ChatGPT before typing.")
    ] = 3.0,
    response_timeout_seconds: Annotated[
        float, typer.Option("--response-timeout-seconds", min=1.0, help="Maximum seconds to wait for a response per cycle.")
    ] = 180.0,
    poll_seconds: Annotated[float, typer.Option("--poll-seconds", min=0.25, help="How often to poll the page while waiting for the response.")] = 1.0,
    stable_seconds: Annotated[
        float, typer.Option("--stable-seconds", min=0.5, help="Response text must stay unchanged this long before it is considered done.")
    ] = 2.0,
    keep_tabs: Annotated[bool, typer.Option("--keep-tabs/--close-tabs", help="Keep each ChatGPT tab open after a cycle.")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Pick and print a question without connecting to the browser.")] = False,
) -> None:
    """Open ChatGPT in a new tab, send a random question, print the response, and repeat."""

    questions = load_questions(question, questions_file)
    interval_seconds = interval_minutes * 60

    summary = Table.grid(padding=(0, 1))
    summary.add_column(style="bold")
    summary.add_column()
    summary.add_row("CDP URL", cdp_url)
    summary.add_row("ChatGPT URL", chatgpt_url)
    summary.add_row("Interval", f"{interval_minutes:g} minute(s)")
    summary.add_row("Cycles", "infinite" if cycles is None else str(cycles))
    summary.add_row("Question pool", str(len(questions)))
    summary.add_row("Tabs", "keep open" if keep_tabs else "close after each cycle")
    console.print(Panel(summary, title="Configuration", border_style="blue"))

    try:
        asyncio.run(
            run_loop(
                cdp_url=cdp_url,
                chatgpt_url=chatgpt_url,
                interval_seconds=interval_seconds,
                cycles=cycles,
                questions=questions,
                seed=seed,
                pre_submit_wait_seconds=pre_submit_wait_seconds,
                response_timeout_seconds=response_timeout_seconds,
                poll_seconds=poll_seconds,
                stable_seconds=stable_seconds,
                keep_tabs=keep_tabs,
                dry_run=dry_run,
            )
        )
    except KeyboardInterrupt:
        console.print(Text("Stopped.", style="yellow"))
    except StopRequested:
        console.print(Text("Stopped.", style="yellow"))


if __name__ == "__main__":
    app()
