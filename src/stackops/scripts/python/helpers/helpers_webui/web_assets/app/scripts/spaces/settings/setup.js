import { h, icon } from "/assets/scripts/dom.js";
import { agentButton } from "../../agent_ask.js";
import { filePlace } from "../../agent_places.js";
import { replay, rise } from "../../motion.js";
import { backLink, editButton } from "../../space_kit.js";
import { button, callout, emojiTile, notice, skeleton } from "../../widgets.js";
import { reasonOf, setup } from "./model.js";
import { createAgentPicker, describeStep } from "./setup/steps.js";
import { BACK_LABEL, HASH, SETUP_HASH, STEPS, WIZARD_PATH, WIZARD_TITLE, stepsDone } from "./words.js";

const MARKS = { true: "Set up", false: "Not set up", null: "Cannot be read" };
const DEFAULTS = { title: "the StackOps defaults", kind: "config" };
const PLACE = {
  title: "Guided setup", commands: ["devops config setup"],
  about: "The things StackOps asks about once: the default cloud, email, coding agent and multiplexer, and a first backup, dotfile, layout and vault.",
  ideas: ["Set up what is still missing here"],
};
// The step whoever opened the tool asked for, and what they filled in, until the page shows them.
let arrival = { step: "", preset: {} };

// The guided commands land here, each on its own step. A value handed over is put in its box and never saved unasked.
export function open(_context, { preset, step }) {
  arrival = { step: step ?? "", preset: preset ?? {} };
  const address = arrival.step ? `${SETUP_HASH}/${arrival.step}` : SETUP_HASH;
  if (location.hash === address) window.dispatchEvent(new HashChangeEvent("hashchange"));
  else location.hash = address;
}

// Home › Guided setup, at #/home/setup: the eight things `devops config setup` asks about, as a list of steps that says what is set
// and what is not, each with its own way to set it. A page and not a sheet: it is a checklist to come back to.
export function createPart({ activity, tools }) {
  let spot = "";
  const agentPicker = createAgentPicker({ activity });
  const count = h("strong", { text: "…" });
  const line = h("p", { text: "Reading this machine…" });
  const bar = h("div", { class: "settings-setup-bar" }, STEPS.map(() => h("i")));
  const hero = h("section", { class: "settings-setup-hero" }, h("div", { class: "settings-setup-count" }, count, h("span", { text: `of ${STEPS.length} set up` })), h("div", { class: "settings-setup-progress" }, bar, line));
  const notes = h("div", { class: "settings-setup-notes" });
  const list = h("ol", { class: "settings-setup-list" }, skeleton(5, "row"));
  const rows = new Map();

  function paint({ value, failure }) {
    element.classList.toggle("loading", setup.reading.loading);
    if (!value) {
      notes.replaceChildren(...(failure ? [notice({ glyph: "alert", tone: "bad", title: "The setup could not be read", body: reasonOf(failure), action: button({ label: "Try again", glyph: "refresh", small: true, onclick: () => setup.reload() }) })] : []));
      hero.hidden = list.hidden = Boolean(failure);
      return;
    }
    hero.hidden = list.hidden = false;
    const done = stepsDone(value);
    const finished = STEPS.filter((step) => done[step.id]).length;
    const next = STEPS.find((step) => done[step.id] === false);
    count.textContent = String(finished);
    [...bar.children].forEach((segment, index) => (segment.className = done[STEPS[index].id] ? "done" : done[STEPS[index].id] === null ? "unknown" : ""));
    line.textContent = next ? `Next: ${next.title.toLowerCase()}. Each step is set here or on the page that owns it.` : finished === STEPS.length ? "Everything is set up. Any step can be changed again." : "Some steps cannot be read until the problems below are fixed.";
    notes.replaceChildren(
      ...[
        value.settings_problem &&
          callout({
            tone: "bad", title: "The StackOps defaults file does not pass its check", text: value.settings_problem.replaceAll(`: ${value.settings_path}`, "").replaceAll(value.settings_path, "the file"),
            extra: h("div", { class: "view-actions" }, agentButton(activity, filePlace(DEFAULTS, { notes: [`The web UI's check of this file says: ${value.settings_problem}`], ideas: ["Fix what is wrong with this file"] }), { small: true }), editButton(activity, DEFAULTS, { label: "Edit the file", small: true })),
          }),
        !value.dotfiles_folder &&
          callout({ tone: "", title: "Your dotfiles folder is not on this machine yet", text: "Each step creates what it needs there. To bring your settings over from another machine instead, use Dotfiles.", href: "#/dotfiles" }),
      ].filter(Boolean),
    );
    agentPicker.paint(value);
    const fresh = rows.size === 0;
    for (const [index, step] of STEPS.entries()) {
      if (!rows.has(step.id)) rows.set(step.id, h("li", { class: "settings-step", "data-step": step.id, tabindex: "-1" }));
      const row = rows.get(step.id);
      const words = describeStep(step, { value, done, activity, tools, agentPicker });
      const held = row.contains(document.activeElement) && document.activeElement.dataset.action === "main";
      row.className = `settings-step ${done[step.id] ? "done" : done[step.id] === null ? "unknown" : "todo"}`;
      row.replaceChildren(
        h("span", { class: "settings-step-mark", title: MARKS[done[step.id]] }, done[step.id] ? icon("check", 15) : String(index + 1)),
        emojiTile(step.emoji, step.path, 40),
        h("div", { class: "settings-step-text" }, h("h3", { text: step.title }), words.state && h("p", { class: "settings-step-state", text: words.state }), words.problem && h("p", { class: "settings-step-problem", text: words.problem }), h("p", { class: "settings-step-about", text: words.about })),
        h("div", { class: "settings-step-actions" }, words.actions),
      );
      if (held) row.querySelector('[data-action="main"]')?.focus({ preventScroll: true });
    }
    if (fresh) {
      list.replaceChildren(...rows.values());
      rise(list);
    }
    if (spot && rows.has(spot)) land();
  }

  // The step the address names: brought into view and marked once, with the keyboard on its button, or in its box where it has one.
  function land() {
    const row = rows.get(spot);
    if (arrival.step === "agent" && typeof arrival.preset.agent === "string") agentPicker.propose(arrival.preset.agent);
    spot = "";
    arrival = { step: "", preset: {} };
    row.scrollIntoView({ block: "center" });
    replay(row, "settings-spot");
    (row.querySelector('[data-action="main"]:enabled, a[data-action="main"]') ?? row.querySelector("input") ?? row).focus({ preventScroll: true });
  }

  const again = button({ label: "Check again", glyph: "refresh", title: "Read the settings on this machine again", onclick: () => setup.reload() });
  again.classList.add("settings-again");
  const element = h(
    "div",
    { class: "settings-setup", hidden: true },
    h(
      "header",
      { class: "view-head" },
      h("div", { class: "view-title" }, backLink(HASH, BACK_LABEL), h("h1", { text: "Guided setup" }), h("p", { text: "Eight things StackOps asks about once. See which are set, and set the rest one at a time." })),
      h("div", { class: "view-actions" }, agentButton(activity, PLACE), button({ label: WIZARD_TITLE, glyph: "sparkle", title: "One guided run for a new machine, in the activity panel", onclick: () => tools.open(WIZARD_PATH) }), again),
    ),
    hero,
    notes,
    list,
  );
  setup.watch(element, paint);

  return {
    element,
    show(rest) {
      spot = STEPS.some((step) => step.id === rest[0]) ? rest[0] : "";
      if (setup.reading.value) paint(setup.reading);
      setup.sync();
    },
  };
}
