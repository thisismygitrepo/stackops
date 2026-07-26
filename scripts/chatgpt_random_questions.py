#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "playwright>=1.49.0",
#   "rich>=13.9.0",
#   "typer>=0.15.0",
# ]
# ///

from __future__ import annotations

import asyncio
import random
import re
import signal
import time
from pathlib import Path
from typing import Annotated, Optional

import typer
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError, async_playwright
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
    "What is a simple way to plan tomorrow in five minutes?",
    "Give me a realistic strategy for starting a task I have been avoiding.",
    "How can I make a recurring chore less annoying?",
    "Suggest a tiny habit that makes mornings calmer.",
    "What is one useful rule for deciding what not to do today?",
    "How can I protect an hour of focused work on a busy day?",
    "Give me a practical way to recover after an unproductive afternoon.",
    "What is a low-effort system for keeping track of commitments?",
    "How can I make my to-do list more actionable?",
    "Suggest a short end-of-day reflection that does not feel tedious.",
    "What is a good way to break a large project into a first step?",
    "How can I decide whether a meeting really needs to happen?",
    "Give me a checklist for preparing for a difficult conversation.",
    "What is one respectful way to say no to a request?",
    "How can I write a clearer email in half the usual time?",
    "Suggest a method for remembering names when meeting people.",
    "What is one useful question to ask before making a purchase?",
    "How can I set up my workspace to reduce distractions?",
    "Give me a simple system for keeping useful notes.",
    "What is an effective way to review a week and learn from it?",
    "Teach me a concept from physics using an everyday analogy.",
    "Explain why the sky changes color at sunrise and sunset.",
    "What is the difference between weather and climate?",
    "Explain entropy without using equations.",
    "How do vaccines train the immune system?",
    "Why does metal feel colder than wood at the same temperature?",
    "Explain how GPS knows where a phone is.",
    "What makes a bridge structurally strong?",
    "Teach me how a refrigerator moves heat.",
    "Why do leaves change color in autumn?",
    "Explain the greenhouse effect clearly and accurately.",
    "What is one surprising fact about the human brain?",
    "How does a solar eclipse happen?",
    "Explain the difference between a virus and a bacterium.",
    "Why do we have leap years?",
    "How do noise-cancelling headphones work?",
    "What is a simple explanation of quantum computing?",
    "Explain how a neural network learns at a high level.",
    "What is a useful scientific question I could explore at home?",
    "Give me a short experiment using ordinary kitchen items.",
    "Teach me a beginner-friendly idea from economics.",
    "Explain compound interest with a small numerical example.",
    "What is opportunity cost, and where might I notice it today?",
    "Explain supply and demand without a graph.",
    "What is the difference between correlation and causation?",
    "Teach me one cognitive bias and how to notice it in myself.",
    "Explain the sunk-cost fallacy with an everyday example.",
    "What does it mean to think in probabilities?",
    "Give me a simple framework for comparing two choices.",
    "What is a common reasoning mistake in online arguments?",
    "Explain Bayes' rule intuitively, without heavy math.",
    "What is a useful way to distinguish a fact, inference, and opinion?",
    "Teach me a small idea from game theory.",
    "Why do averages sometimes mislead people?",
    "Explain the difference between median and mean using a real scenario.",
    "Give me a short logic puzzle, then wait for my answer before revealing it.",
    "Teach me a mental model that helps with long-term decisions.",
    "Explain a famous paradox in a way a teenager could understand.",
    "Give me a writing prompt set in a place that does not exist.",
    "Give me a character with a secret, a goal, and an obstacle.",
    "Suggest an opening line for a mystery story.",
    "Give me three unusual metaphors for feeling hopeful.",
    "Invent a folktale premise in two sentences.",
    "Give me a dialogue prompt between two people who want opposite things.",
    "Describe a fictional city built around one strange rule.",
    "Give me a constrained writing exercise that takes ten minutes.",
    "Suggest a poem idea based on an ordinary object.",
    "Write a scene prompt with no dialogue allowed.",
    "Give me a plot twist that is surprising but fair.",
    "Invent a board game and explain its core mechanic.",
    "Create a tiny worldbuilding challenge for me.",
    "Give me a visual-art prompt using only two colors.",
    "Suggest a photography challenge I can do on a walk.",
    "Give me an idea for a short comic with an unexpected final panel.",
    "Invent a product that solves a small but oddly specific problem.",
    "Give me a design challenge for improving an everyday object.",
    "Suggest a playlist theme that tells a story without lyrics.",
    "Give me a creative constraint that could make a project more interesting.",
    "Teach me the basic structure of a satisfying short story.",
    "Tell me an overlooked historical event worth learning about.",
    "What lesson can we take from the history of public health?",
    "Explain how the printing press changed everyday life.",
    "Tell me about an invention whose original purpose was unexpected.",
    "What was daily life like in one ancient civilization?",
    "Explain one major turning point in the history of computing.",
    "Teach me about a historical figure who changed their mind publicly.",
    "What is a historical example of a small event having large consequences?",
    "Explain the origin of a familiar word or phrase.",
    "Tell me how a common food became popular in a different culture.",
    "What is a tradition from somewhere in the world and what does it mean?",
    "Introduce me to a work of art and how to look at it.",
    "Recommend a classic book based on a mood rather than a genre.",
    "Explain what makes a film scene memorable without spoilers.",
    "Teach me how to listen actively to a piece of music.",
    "Tell me about an architectural style and how to recognize it.",
    "What is a useful way to visit a museum when I feel overwhelmed?",
    "Introduce me to a philosopher and one practical idea from their work.",
    "Explain a philosophical question that has no easy answer.",
    "Give me a simple dinner idea that uses beans or lentils.",
    "Suggest a quick breakfast that is filling and inexpensive.",
    "What can I cook when I have eggs, rice, and a few vegetables?",
    "Teach me one knife skill that makes cooking easier.",
    "How can I make leftovers feel like a new meal?",
    "Give me a meal-prep idea for a busy week.",
    "What are three ways to make a simple soup more flavorful?",
    "Suggest a pantry meal with a flexible ingredient list.",
    "How can I learn to season food more confidently?",
    "Give me a dessert idea with five ingredients or fewer.",
    "What is a useful grocery-shopping rule for reducing food waste?",
    "Suggest a packed lunch that does not need reheating.",
    "What is a good caffeine-free drink to make at home?",
    "Teach me how to make a basic vinaigrette and vary it.",
    "Give me a simple recipe inspired by a cuisine I may not know well.",
    "What is one small cooking project that teaches several skills?",
    "Give me a beginner Python exercise involving strings.",
    "Give me a Python debugging puzzle with a hint but no answer yet.",
    "Explain one software design principle with a concrete example.",
    "What is the difference between a process and a thread?",
    "Teach me how HTTP works from a browser request to a response.",
    "Explain what a database index is and when it helps.",
    "What is one practical Git habit that prevents mistakes?",
    "Explain the difference between encryption and hashing.",
    "Teach me a command-line concept that saves time.",
    "What is a simple way to evaluate whether a source online is trustworthy?",
    "Explain why software estimates are often wrong.",
    "Give me a small algorithm challenge suitable for a beginner.",
    "What makes an API pleasant to use?",
    "Explain one accessibility practice that improves a website for everyone.",
    "Teach me the difference between authentication and authorization.",
    "What is caching, and what problem can it create?",
    "Explain a useful regular expression in plain English.",
    "Give me a security habit that has a large payoff.",
    "Teach me how to spot a misleading chart.",
    "What is a good first project for learning a new programming language?",
    "Give me a 15-minute bodyweight movement routine with gentle options.",
    "Suggest a simple stretch break for someone who sits at a desk.",
    "What is one evidence-based way to improve sleep habits?",
    "How can I take a walk that feels mentally refreshing?",
    "Give me a low-pressure idea for reconnecting with a friend.",
    "What is a kind question I can ask someone having a hard day?",
    "Suggest a short mindfulness exercise for a distracted moment.",
    "What is a practical way to reduce notification overload?",
    "How can I make a weekend feel restorative instead of rushed?",
    "Give me a simple practice for noticing what is going well.",
    "What is a healthy boundary I could consider setting?",
    "How can I be more present during a conversation?",
    "Suggest a small act of generosity that costs little or nothing.",
    "What is one way to make exercise more enjoyable?",
    "Give me an idea for a screen-free evening activity.",
    "How can I prepare for travel with less stress?",
    "Give me a beginner-friendly budget exercise using imaginary numbers.",
    "What is a simple way to understand my monthly spending?",
    "How can I decide whether a subscription is worth keeping?",
    "Give me three questions to ask before accepting a financial offer.",
    "What is a low-cost way to make my home more comfortable?",
    "Suggest a weekend project that improves everyday life.",
    "How can I start learning a language in ten minutes a day?",
    "Teach me five useful phrases in a language of your choice.",
    "Give me a memory technique for learning vocabulary.",
    "What is one skill I could practice deliberately this week?",
    "Suggest a mini curriculum for exploring a topic over seven days.",
    "What is a good question to ask an expert in any field?",
    "Teach me how to give more useful feedback on someone else's work.",
    "What is a respectful way to disagree without making the conversation worse?",
    "Give me a question that helps uncover assumptions in a discussion.",
    "What is a simple negotiation principle I can use in everyday life?",
    "Suggest a way to make an apology more sincere and useful.",
    "What is one way to make a group decision more inclusive?",
    "Teach me a facilitation technique for a small meeting.",
    "Give me a thought experiment about technology and society.",
    "What is one ethical question raised by artificial intelligence?",
    "Explain a current environmental challenge and one meaningful response to it.",
    "What is a local action that can make a neighborhood better?",
    "Give me a beginner stargazing challenge for the next clear night.",
    "Tell me an interesting fact about an animal and why it matters.",
    "What is a surprising feature of a plant I might see nearby?",
    "Teach me how to identify one common constellation.",
    "Give me a nature-journaling prompt for a park or garden.",
    "What is one question that makes an ordinary walk more curious?",
    "Give me a short riddle with an answer that is not obvious.",
    "Invent a puzzle based on patterns or sequences.",
    "Give me a lateral-thinking puzzle and reveal the answer only when I ask.",
    "Teach me a card trick principle without requiring special equipment.",
    "Give me a surprising trivia question, then explain the answer.",
    "What is a fun challenge I can complete in the next twenty minutes?",
    "Suggest a micro-adventure that can happen close to home.",
    "Give me a random topic to research for exactly fifteen minutes.",
    "Ask me five thoughtful questions, one at a time, to help me reflect on today.",
    "Ask me a question that could lead to a surprisingly good conversation.",
    "What is one thing I might be overlooking because it feels too familiar?",
    "Give me a prompt for writing a letter to my future self.",
    "What is a small experiment I could run to learn something about my habits?",
    "Suggest a question I can use to end the day with curiosity instead of judgment.",
]


app = typer.Typer(
    add_completion=False,
    help=(
        "Send random local questions to ChatGPT through an existing logged-in "
        "Chrome/Chromium CDP session."
    ),
)
console = Console()


class StopRequested(Exception):
    pass


async def find_composer(page: Page):
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


async def wait_for_response(
    page: Page,
    *,
    timeout_seconds: float,
    poll_seconds: float,
    stable_seconds: float,
) -> str:
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

    return await wait_for_response(
        page,
        timeout_seconds=response_timeout_seconds,
        poll_seconds=poll_seconds,
        stable_seconds=stable_seconds,
    )


def load_questions(question_options: Optional[list[str]], questions_file: Optional[Path]) -> list[str]:
    questions: list[str] = []

    if question_options:
        questions.extend(q.strip() for q in question_options if q.strip())

    if questions_file:
        if not questions_file.exists():
            raise typer.BadParameter(f"questions file does not exist: {questions_file}")
        file_questions = [
            line.strip()
            for line in questions_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
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
        SpinnerColumn(),
        TextColumn(f"Waiting {seconds:g}s before cycle {cycle + 1}"),
        TimeElapsedColumn(),
        transient=True,
        console=console,
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
    cycles: Optional[int],
    questions: list[str],
    seed: Optional[int],
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
        str,
        typer.Option(
            "--cdp-url",
            help="Chrome DevTools Protocol endpoint for the already-running browser.",
        ),
    ] = "http://192.168.0.13:9999",
    chatgpt_url: Annotated[
        str,
        typer.Option("--chatgpt-url", help="ChatGPT URL to open in each new tab."),
    ] = "https://chatgpt.com/",
    interval_minutes: Annotated[
        float,
        typer.Option(
            "--interval-minutes",
            "-i",
            min=0.0,
            help="Minutes to wait between cycles. Default is 10 minutes.",
        ),
    ] = 10.0,
    cycles: Annotated[
        Optional[int],
        typer.Option(
            "--cycles",
            "-n",
            min=1,
            help="Number of cycles to run. Omit for infinite repeat.",
        ),
    ] = None,
    question: Annotated[
        Optional[list[str]],
        typer.Option(
            "--question",
            "-q",
            help="Question to include in the random pool. Can be passed multiple times.",
        ),
    ] = None,
    questions_file: Annotated[
        Optional[Path],
        typer.Option(
            "--questions-file",
            "-f",
            exists=False,
            dir_okay=False,
            help="Newline-delimited question file. Empty lines and # comments are ignored.",
        ),
    ] = None,
    seed: Annotated[
        Optional[int],
        typer.Option("--seed", help="Random seed for reproducible question selection."),
    ] = None,
    pre_submit_wait_seconds: Annotated[
        float,
        typer.Option(
            "--pre-submit-wait-seconds",
            min=0.0,
            help="Seconds to wait after opening ChatGPT before typing.",
        ),
    ] = 3.0,
    response_timeout_seconds: Annotated[
        float,
        typer.Option(
            "--response-timeout-seconds",
            min=1.0,
            help="Maximum seconds to wait for a response per cycle.",
        ),
    ] = 180.0,
    poll_seconds: Annotated[
        float,
        typer.Option(
            "--poll-seconds",
            min=0.25,
            help="How often to poll the page while waiting for the response.",
        ),
    ] = 1.0,
    stable_seconds: Annotated[
        float,
        typer.Option(
            "--stable-seconds",
            min=0.5,
            help="Response text must stay unchanged this long before it is considered done.",
        ),
    ] = 2.0,
    keep_tabs: Annotated[
        bool,
        typer.Option("--keep-tabs/--close-tabs", help="Keep each ChatGPT tab open after a cycle."),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Pick and print a question without connecting to the browser."),
    ] = False,
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
