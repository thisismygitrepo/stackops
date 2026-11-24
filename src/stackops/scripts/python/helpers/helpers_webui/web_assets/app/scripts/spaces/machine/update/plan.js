import { h, icon } from "/assets/scripts/dom.js";
import { pill } from "../../../widgets.js";
import { plural } from "../../../words.js";
import { developerEffects, stepsOf } from "./steps.js";
import { home, remoteName } from "./words.js";

const NAMES_SHOWN = 12;
const TITLES = {
  refresh: "Refresh StackOps's own scripts and settings",
  settings: "Replace my app settings with the packaged ones",
  shell: "Set up my shell's startup file",
  developer: "Commit and push my changes first",
};

// One switch with what it does in a sentence, and under it what that means on this machine right now. The switch is made once and only its
// state and words change afterwards, so it keeps the keyboard focus while the page repaints.
function optionRow(id, onToggle) {
  const hint = h("p", { class: "field-hint" });
  const toggle = h("button", { class: "field toggle-row", type: "button", role: "switch", onclick: () => onToggle(id) }, h("div", {}, h("div", { class: "field-label" }, h("span", { text: TITLES[id] })), hint), h("i", { class: "switch" }));
  const facts = h("div", { class: "machine-update-option-facts" });
  return { element: h("div", { class: "machine-update-option", "data-option": id }, toggle, facts), toggle, hint, facts };
}

const remark = (tone, glyph, ...content) => h("p", { class: `machine-update-remark ${tone}` }, icon(glyph, 15), h("span", {}, ...content));

// The update's choices in plain words, and beside them the steps those choices add up to, in the order they run.
export function createPlan({ options, onChange }) {
  const toggle = (id) => {
    options[id] = !options[id];
    onChange();
  };
  const rows = Object.fromEntries(Object.keys(TITLES).map((id) => [id, optionRow(id, toggle)]));
  const steps = h("ol", { class: "machine-update-steps" });
  const element = h(
    "section",
    { class: "machine-update-card machine-update-plan" },
    h("header", { class: "machine-update-card-head" }, h("h2", { text: "What the update does" })),
    h("div", { class: "machine-update-plan-body" }, h("div", { class: "machine-update-options" }, h("h3", { text: "Your choices" }), Object.values(rows).map((row) => row.element)), h("div", {}, h("h3", { text: "In this order" }), steps)),
  );

  function paintSettings(effects) {
    const found = effects?.settings;
    rows.settings.hint.textContent = "For every program StackOps ships settings for, this deletes the settings file you have and puts the packaged one in its place. No copy of yours is kept.";
    if (!found) {
      rows.settings.facts.replaceChildren();
      return;
    }
    const names = found.present.slice(0, NAMES_SHOWN);
    rows.settings.facts.replaceChildren(
      remark(options.settings ? "warn" : "", options.settings ? "alert" : "info", `It covers ${plural(found.programs, "program")}. ${found.present.length === 0 ? "None of them has settings on this machine yet, so nothing of yours is lost." : `${found.present.length} of them ${found.present.length === 1 ? "has" : "have"} settings on this machine now, which is what goes.`}`),
      names.length > 0 && h("div", { class: "machine-update-names" }, names.map((name) => h("span", { text: name })), found.present.length > names.length && h("span", { class: "more", text: `and ${found.present.length - names.length} more` })),
    );
  }

  function paintDeveloper(state) {
    const row = rows.developer;
    const applies = state.route === "checkout" && state.checkout.problem === "";
    row.element.hidden = !applies;
    if (!applies) {
      options.developer = false;
      return;
    }
    const { checkout } = state;
    const stopped = checkout.branch === "" ? "No branch is checked out, so there is nothing to push." : checkout.origin === "" ? "The folder has no remote called origin to push to." : "";
    if (stopped) options.developer = false;
    row.toggle.disabled = stopped !== "";
    row.hint.textContent = `Before anything else, this commits every change in ${home(checkout.path)}, pulls, and pushes${checkout.origin ? ` to ${remoteName(checkout.origin)}` : ""}. It is for a source folder you publish from.`;
    row.facts.replaceChildren(
      ...(stopped
        ? [remark("", "info", stopped)]
        : [h("div", { class: `machine-update-consequence ${options.developer ? "on" : ""}` }, h("strong", {}, icon("alert", 15), options.developer ? "This will happen first" : "Switched on, this would happen first"), h("ol", {}, developerEffects(state).map((text) => h("li", { text }))))]),
    );
  }

  function paint({ state, effects }) {
    paintDeveloper(state);
    for (const [id, row] of Object.entries(rows)) row.toggle.setAttribute("aria-checked", String(options[id]));
    rows.refresh.hint.textContent = `Copies the scripts and default settings that come with StackOps into ${effects ? home(effects.config_folder) : "its settings folder"}, over the copies there. Those are StackOps's own files, not yours.`;
    rows.refresh.facts.replaceChildren(...(options.refresh ? [] : [remark("warn", "alert", "Left off, the old scripts stay, and they may not match the new version.")]));
    paintSettings(effects);
    const shell = effects?.shell;
    rows.shell.hint.textContent = `Adds one line to ${shell ? home(shell.profile) : "your shell's startup file"} so that every new terminal loads StackOps. The rest of the file stays as it is.`;
    rows.shell.facts.replaceChildren(...(shell ? [remark("", shell.loaded ? "check" : "info", shell.loaded ? [pill("Already there", "good"), " The line is in the file, so this changes nothing."] : "The line is not in the file yet.")] : []));
    steps.replaceChildren(
      ...stepsOf(state, effects, options).map((step, index) => h("li", { class: step.tone }, h("i", { class: "num", text: step.tone === "you" ? "" : String(index + 1) }, step.tone === "you" && icon("power", 13)), h("div", {}, h("strong", { text: step.title }), h("p", { text: step.detail }), step.extra)),
      ),
    );
  }

  return { element, paint };
}
