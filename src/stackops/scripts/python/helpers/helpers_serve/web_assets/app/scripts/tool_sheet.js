import { debounce, h, icon, toast } from "/assets/scripts/dom.js";
import { nodeHash, state } from "/assets/scripts/state.js";
import { ARRIVAL_VALUES, ESSENTIAL_FLAGS, LIVE_NAMES, LIVE_PATHS, OMITTED_FIELDS, PASSTHROUGH_TOOLS } from "./catalog.js";
import { commandDetail, query } from "./data.js";
import { createFriendlyForm } from "./friendly_form.js";
import { noteOpened, recall, remember } from "./memory.js";
import { openSheet } from "./overlays.js";
import { renderResult } from "./result_view.js";
import { button, emojiTile, notice, outputActions, skeleton } from "./widgets.js";
import { friendlyText, fullTitleOf, titleOf, trailOf } from "./words.js";

const RELOAD_DELAY_MILLISECONDS = 400;
const JSON_FLAG = "--json";
const REPORT_FLAG = "--as-html";
// The command tree only describes declared parameters, so a tool that passes the rest on gets this field added here.
// Design choice: it follows the form's rule for arguments, so the ones before it must be filled in first; that is what keeps a pass-through value out of an earlier argument's place.
const EXTRA_ARGUMENTS = {
  name: "extra_arguments", kind: "argument", flags: [], off_flags: [], control: "text", choices: [], multiple: true, required: false, default: "",
  help: "Passed on to the script or program as they are.",
};

// The one place any tool opens: read-only tools show their result straight away, the rest wait for the button.
// `guides` maps a command path to a function that opens a purpose-built sheet in place of the generic one.
export function createToolSheet({ activity, openReport, guides = {} }) {
  // `title` renames the sheet for a caller that uses a tool for something narrower than its name says, such as editing through "Add a backup".
  async function open(path, { preset = {}, title: givenTitle } = {}) {
    const node = state.nodes.get(path);
    if (!node || node.kind !== "command") return toast(`There is no tool at “${path}”.`);
    noteOpened(path);
    if (guides[path]) return guides[path]();
    const title = givenTitle ?? titleOf(node);
    const pathTokens = path.split(" ");
    const sheet = openSheet({ label: title, wide: true });
    const formHolder = h("div", { class: "tool-form" }, skeleton(2, "row"));
    const resultHolder = h("div", { class: "tool-result" });
    sheet.body.append(
      h("header", { class: "tool-head" }, emojiTile(node.icon || "✨", node.path, 56), h("div", {}, h("span", { class: "overline", text: trailOf(node) || "StackOps" }), h("h1", { text: title }), h("p", { text: friendlyText(node.summary) }))),
      formHolder,
      resultHolder,
    );

    let parameters = null;
    try {
      ({ parameters } = await commandDetail(path));
    } catch (error) {
      formHolder.replaceChildren(notice({ glyph: "alert", tone: "bad", title: "This tool's options could not be read", body: error.message }));
      return;
    }
    // An omitted parameter is dropped here, not just hidden, so a remembered or pre-filled value for it can never reach the command either.
    const omitted = OMITTED_FIELDS[path] ?? [];
    const specs = [...(parameters ?? []).filter((spec) => !omitted.includes(spec.name)), ...(PASSTHROUGH_TOOLS.has(path) ? [EXTRA_ARGUMENTS] : [])];
    const flagged = (flag) => specs.some((spec) => spec.flags.includes(flag));
    // A read-only tool queries on arrival and again on every change. One that still needs something typed shows its form and queries once that is filled in.
    const live = LIVE_NAMES.has(node.name) || LIVE_PATHS.has(path);
    const starting = new Map(Object.entries({ ...ARRIVAL_VALUES[path], ...preset }));
    // A read-only tool reopens the way it was left, with whatever the caller filled in on top. Reset goes back to `starting`.
    const recalled = live ? recall(path) : new Map();
    const values = recalled.size > 0 ? new Map([...recalled, ...Object.entries(preset)]) : new Map(starting);
    // A read-only tool that only needs a pick from a short list starts on the first one, so there is something to look at straight away.
    if (live) for (const filled of [starting, values]) for (const spec of specs) if (spec.required && spec.control === "choice" && !spec.multiple && !filled.has(spec.name)) filled.set(spec.name, spec.choices[0]);
    const problem = h("span", { class: "tool-problem" });
    let shown = { text: "" };
    const outputButtons = outputActions(() => shown.text, pathTokens.join("-"));
    const offerOutput = (result) => {
      shown = result;
      for (const item of outputButtons) item.hidden = !result.text;
    };
    offerOutput(shown);
    let ticket = 0;
    let touched = false;

    async function load(fresh) {
      const { tokens, problems } = form.collect();
      if (problems.length) return;
      const mine = (ticket += 1);
      resultHolder.classList.add("loading");
      if (!resultHolder.hasChildNodes()) resultHolder.replaceChildren(...skeleton(4, "row"));
      try {
        // The flag goes first: after an argument that starts with a dash the form writes `--`, and anything behind that is read as one more argument.
        const result = await query([...pathTokens, ...(flagged(JSON_FLAG) ? [JSON_FLAG] : []), ...tokens], fresh);
        if (mine !== ticket) return;
        resultHolder.replaceChildren(renderResult(result));
        offerOutput(result);
      } catch (error) {
        if (mine !== ticket) return;
        offerOutput({ text: "" });
        // Design choice: a tool that has options and fails before any was changed is usually asking for a choice the CLI does not mark as required
        // (an account name, say), so it gets a calm notice with the CLI's own words. It is red once the person has set something.
        const waiting = !touched && form.count > 0;
        resultHolder.replaceChildren(
          notice({
            glyph: waiting ? "sliders" : "alert", tone: waiting ? "" : "bad", title: waiting ? "Nothing to show yet" : "This didn't work", body: error.message,
            action: button({ label: "Try again", glyph: "refresh", small: true, onclick: () => load(true) }),
          }),
        );
      }
      resultHolder.classList.remove("loading");
    }

    const reloadSoon = debounce(() => load(false), RELOAD_DELAY_MILLISECONDS);
    const form = createFriendlyForm({
      // Whatever the sheet opens with stays in view, so a pre-filled or remembered choice is never tucked away under "More options".
      parameters: specs, values, essentials: [...(ESSENTIAL_FLAGS[path] ?? []), ...specs.filter((spec) => values.has(spec.name)).flatMap((spec) => spec.flags)],
      onChange: () => {
        touched = true;
        const { problems } = form.collect();
        problem.textContent = problems[0] ?? "";
        primary.disabled = problems.length > 0;
        if (!live) return;
        remember(path, form.filled());
        reloadSoon();
      },
    });

    async function run() {
      const { tokens, problems } = form.collect();
      if (problems.length) return;
      try {
        await activity.start({ title: givenTitle ?? fullTitleOf(node), emoji: node.icon, arguments: [...pathTokens, ...tokens], interactive: true, reveal: true });
        sheet.close();
      } catch (error) {
        toast(error.message);
      }
    }

    const primary = live ? button({ label: "Refresh", glyph: "refresh", tone: "primary", onclick: () => load(true) }) : button({ label: title.length <= 24 ? title : "Start", glyph: "play", tone: "primary", onclick: run });
    const reportButton =
      flagged(REPORT_FLAG) &&
      button({
        label: "Open as a report", glyph: "report",
        onclick: () => {
          const { tokens } = form.collect();
          sheet.close();
          openReport({ title, blurb: friendlyText(node.summary), arguments: [...pathTokens, REPORT_FLAG, ...tokens.filter((token) => token !== REPORT_FLAG)] });
        },
      });
    const note = parameters === null ? "This tool asks for what it needs once it starts." : "Nothing to fill in — it is ready to go.";
    formHolder.replaceChildren(...(form.count > 0 ? [form.element] : live ? [] : [h("p", { class: "tool-note", text: note })]));
    formHolder.hidden = !formHolder.hasChildNodes();
    sheet.foot.hidden = false;
    sheet.foot.append(
      ...[
        h("a", { class: "dev-link", href: `/dev${nodeHash(node)}`, title: "Open this tool in the developer view" }, icon("code", 14), h("span", { text: "Developer view" })),
        problem,
        ...outputButtons,
        form.count > 0 && button({ label: "Reset", tone: "ghost", onclick: () => form.reset(starting) }),
        reportButton,
        primary,
      ].filter(Boolean),
    );
    sheet.panel.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) primary.click();
    });
    primary.disabled = form.collect().problems.length > 0;
    if (live) load(false);
  }

  return { open };
}
