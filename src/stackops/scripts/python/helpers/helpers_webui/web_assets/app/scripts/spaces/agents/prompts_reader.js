import { h, icon, tildify } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { agentButton } from "../../agent_ask.js";
import { filePlace } from "../../agent_places.js";
import { replay } from "../../motion.js";
import { editButton } from "../../space_kit.js";
import { button, copyChip, copyText, pathChip, pill, segmented } from "../../widgets.js";
import { hueOf, initialsOf, plural } from "../../words.js";
import { TEXT_VIEWS, markAll, readingStats, renderLooseText } from "./loose_text.js";
import { canChange, editTarget, sourceLabel } from "./prompts_files.js";

const COPIED_MILLISECONDS = 1400;
const NAMED_SOURCES = new Set(["workspace", "user", "library"]);

// "team.updateDocs" reads as "Update docs"; the exact name stays available to copy.
export function titleOfPrompt(name) {
  const words = name.split(".").at(-1).replace(/([a-z0-9])([A-Z])/g, "$1 $2").replace(/([A-Z]+)([A-Z][a-z])/g, "$1 $2").split(/[-_\s]+/).filter(Boolean);
  const text = words.map((word) => (word.length > 1 && /^[A-Z0-9]+$/.test(word) ? word : word.toLowerCase())).join(" ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export const promptFace = (prompt, size) => h("span", { class: "avatar", style: `--hue:${hueOf(prompt.group ?? prompt.name)};--size:${size}px`, text: initialsOf(titleOfPrompt(prompt.name)) });

// What the "Run a prompt" tool needs to pick up exactly this saved prompt, from exactly the file it was read from.
function runPreset(prompt) {
  const where = NAMED_SOURCES.has(prompt.source) ? { source: prompt.source } : { custom_path: prompt.path };
  return { context_name: prompt.name, ...where, ...(prompt.agent ? { agent: prompt.agent } : {}) };
}

function copyButton(text) {
  const face = (glyph, label) => [icon(glyph, 16), h("span", { text: label })];
  const element = h("button", { class: "btn plain", type: "button", title: "Copy the whole prompt" }, face("copy", "Copy"));
  element.addEventListener("click", async () => {
    if (!(await copyText(text))) return;
    element.classList.add("copied");
    element.replaceChildren(...face("check", "Copied"));
    setTimeout(() => {
      element.classList.remove("copied");
      element.replaceChildren(...face("copy", "Copy"));
    }, COPIED_MILLISECONDS);
  });
  return element;
}

export function createPromptReader({ activity, tools, onBack }) {
  let view = "formatted";
  let current = null;
  let currentTerm = "";
  let shownStamp = "";

  const head = h("header", { class: "prompt-head" });
  const blurb = h("p", { class: "prompt-blurb" });
  const meta = h("div", { class: "prompt-meta" });
  const progress = h("i");
  const scroll = h("div", { class: "prompt-scroll", tabindex: "0" });
  const element = h("article", { class: "prompt-reader" }, head, blurb, meta, h("div", { class: "prompt-progress", "aria-hidden": "true" }, progress), scroll);
  const viewPicker = segmented(TEXT_VIEWS, (value) => {
    view = value;
    viewPicker.set(view);
    paintBody();
  });

  const trackProgress = () => {
    const range = scroll.scrollHeight - scroll.clientHeight;
    progress.style.transform = `scaleX(${range > 0 ? Math.min(scroll.scrollTop / range, 1) : 0})`;
  };
  scroll.addEventListener("scroll", trackProgress, { passive: true });

  function paintBody() {
    scroll.replaceChildren(
      view === "plain" ? h("pre", { class: "prompt-plain" }, markAll(current.text, currentTerm)) : renderLooseText(current.text, currentTerm),
      h("footer", { class: "prompt-origin" }, h("span", { text: "Kept in" }), pathChip(current.path)),
    );
    const hit = currentTerm ? scroll.querySelector("mark") : null;
    scroll.scrollTop = hit ? Math.max(0, hit.offsetTop - scroll.clientHeight / 3) : 0;
    trackProgress();
  }

  // Showing the same prompt with the same search word again changes nothing, so a background refresh never moves the reader.
  function show(prompt, term) {
    const stamp = JSON.stringify([prompt.source, prompt.name, prompt.path, prompt.group, prompt.description, prompt.agent, prompt.directory, prompt.text, term]);
    if (stamp === shownStamp) return;
    const moved = !current || current.source !== prompt.source || current.name !== prompt.name;
    shownStamp = stamp;
    current = prompt;
    currentTerm = term;
    const stats = readingStats(prompt.text);
    head.replaceChildren(
      h("button", { class: "icon-btn prompt-back", type: "button", title: "Back to all prompts", "aria-label": "Back to all prompts", onclick: onBack }, icon("back", 16)),
      promptFace(prompt, 46),
      h(
        "div",
        { class: "prompt-title" },
        h("span", { class: "overline", text: [sourceLabel(prompt.source), ...prompt.name.split(".").slice(0, -1), prompt.group].filter(Boolean).join(" · ") }),
        h("h2", { text: titleOfPrompt(prompt.name) }),
      ),
      h(
        "div",
        { class: "prompt-actions" },
        copyButton(prompt.text),
        canChange(prompt) && agentButton(activity, filePlace(editTarget(prompt), { notes: [`The prompt on screen is “${prompt.name}”.`], ideas: ["Rewrite this prompt so that …"] }), { small: true }),
        canChange(prompt) && editButton(activity, editTarget(prompt)),
        button({ label: "Run this prompt", glyph: "play", tone: "primary", title: "Hand this prompt to an agent", onclick: () => tools.open("agents run-prompt", { preset: runPreset(prompt) }) }),
      ),
    );
    blurb.textContent = prompt.description ?? "";
    blurb.hidden = !prompt.description;
    meta.replaceChildren(
      ...[
        copyChip(prompt.name),
        h("span", { class: "dim", text: `${plural(stats.words, "word")} · about ${stats.minutes} min to read` }),
        prompt.agent && pill(`Written for ${prompt.agent}`, "accent"),
        prompt.directory && h("span", { class: "fact", title: "The folder this prompt is meant for" }, icon("folder", 12), tildify(prompt.directory, state.boot.home)),
        h("span", { class: "spacer" }),
        viewPicker.element,
      ].filter(Boolean),
    );
    viewPicker.set(view);
    paintBody();
    if (moved) replay(scroll, "prompt-in");
  }

  return { element, scroll, show, refit: () => viewPicker.set(view) };
}
