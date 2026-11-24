import { h, icon } from "/assets/scripts/dom.js";
import { button } from "../../widgets.js";
import { DOTFILES_HASH } from "./words.js";

const PROMPT_WAIT_MILLISECONDS = 20000;
const PROMPT_POLL_MILLISECONDS = 120;
const REASON_LIMIT = 320;

// The head of a page of this space: the way back, the title, and "Every option" for the command's own form.
export function partHead({ title, lede, actions }) {
  return h(
    "header",
    { class: "view-head" },
    h("div", { class: "view-title" }, h("a", { class: "dotfiles-back", href: DOTFILES_HASH }, icon("back", 14), h("span", { text: "Dotfiles" })), h("h1", { text: title }), h("p", { text: lede })),
    h("div", { class: "view-actions" }, actions),
  );
}

export const everyOption = (tools, path, preset) => button({ label: "Every option", glyph: "sliders", title: "The command's own form, with everything it can do", onclick: () => tools.open(path, { plain: true, preset: preset() }) });
export const stepTitle = (number, text) => h("h3", { class: "dotfiles-step-title" }, h("b", { class: "dotfiles-step", text: String(number) }), text);

// A password box, and one switch that shows what was typed in several of them. `onInput` hears every change.
export function passwordBox({ label, placeholder, onInput }) {
  const input = h("input", { class: "text-input", type: "password", placeholder, "aria-label": label, autocomplete: "new-password", spellcheck: "false", autocapitalize: "off", oninput: () => onInput(input.value) });
  return { element: h("label", { class: "field" }, h("span", { class: "field-label" }, h("span", { text: label })), input), input };
}

export function revealToggle(boxes) {
  const toggle = h("button", { class: "mini-toggle", type: "button", role: "switch", "aria-checked": "false" }, h("i", { class: "switch" }), h("span", { text: "Show what I type" }));
  toggle.addEventListener("click", () => {
    const shown = toggle.getAttribute("aria-checked") !== "true";
    toggle.setAttribute("aria-checked", String(shown));
    for (const box of boxes) box.input.type = shown ? "text" : "password";
  });
  return toggle;
}

const readConsole = (terminal) => {
  const buffer = terminal.buffer.active;
  return Array.from({ length: buffer.length }, (_, index) => buffer.getLine(index)?.translateToString(true) ?? "").join("\n").trimEnd();
};

// Types the archive's password into a running task when the command asks for it, the way the person would in the Activity panel. A design
// choice: the commands take a password from a prompt, a file or an environment variable, and a task started from the page can be given
// neither a file that is safe to leave on disk nor a variable. The prompt reads with the terminal's echo off, so what is typed never shows
// in the console and is kept nowhere. It is typed once, only at the end of the output and only after the exact prompt, and not at all when
// the command warns that it could not switch the echo off. Resolves to "typed", or to why it was not: "unsafe", "unseen", "ended".
export function typeWhenAsked(task, prompt, secret) {
  return new Promise((resolve) => {
    const started = Date.now();
    let over = false;
    task.done.then(() => (over = true));
    const look = () => {
      if (over) return resolve("ended");
      const text = task.terminal ? readConsole(task.terminal) : "";
      if (/may be echoed/i.test(text)) return resolve("unsafe");
      if (text.endsWith(prompt) && task.sendKeys?.(`${secret}\r`)) return resolve("typed");
      if (Date.now() - started > PROMPT_WAIT_MILLISECONDS) return resolve("unseen");
      setTimeout(look, PROMPT_POLL_MILLISECONDS);
    };
    look();
  });
}

// What a task said went wrong, from its console: what stands from its first "Error" line on, or its last line. The line the server closes
// every run with ("[exit 1 · 0.9s]") ends it.
export function reasonOf(task) {
  if (!task.terminal) return "";
  const lines = readConsole(task.terminal).split("\n").map((line) => line.replace(/[│╭╮╰╯─┃┏┓┗┛━]/g, "").trim()).filter(Boolean);
  const closing = lines.findIndex((line) => /^\[(exit \d+|stopped|done) · /.test(line));
  const said = closing < 0 ? lines : lines.slice(0, closing);
  const error = said.findIndex((line) => /^(❌ )?error(:|$)/i.test(line));
  const reason = (error < 0 ? said.slice(-1) : said.slice(/^error$/i.test(said[error]) ? error + 1 : error)).join(" ").replace(/^(❌ )?error:\s*/i, "");
  return reason.length > REASON_LIMIT ? `${reason.slice(0, REASON_LIMIT)}…` : reason;
}

// A banner over a page for a task of its own: a spinner or a mark, what happened, and what can be done about it.
export function runBanner({ tone, busy, title, text, extra, actions }) {
  return h(
    "div",
    { class: `dotfiles-banner ${tone}` },
    h("span", { class: "dotfiles-banner-mark" }, busy ? h("i", { class: "ring" }) : icon(tone === "bad" ? "alert" : tone === "good" ? "check" : "info", 18)),
    h("div", { class: "dotfiles-banner-text" }, h("strong", { text: title }), text && h("p", { text }), extra),
    h("div", { class: "dotfiles-banner-actions" }, actions),
  );
}
