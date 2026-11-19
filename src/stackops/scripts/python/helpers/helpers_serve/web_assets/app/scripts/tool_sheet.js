import { debounce, h, icon, toast } from "/assets/scripts/dom.js";
import { nodeHash, state } from "/assets/scripts/state.js";
import { ESSENTIAL_FLAGS, LIVE_NAMES } from "./catalog.js";
import { commandDetail, query } from "./data.js";
import { createFriendlyForm } from "./friendly_form.js";
import { openSheet } from "./overlays.js";
import { renderResult } from "./result_view.js";
import { button, emojiTile, notice, skeleton } from "./widgets.js";
import { friendlyText, fullTitleOf, titleOf, trailOf } from "./words.js";

const RELOAD_DELAY_MILLISECONDS = 400;
const JSON_FLAG = "--json";
const REPORT_FLAG = "--as-html";

// The one place any tool opens: read-only tools show their result straight away, the rest wait for the button.
export function createToolSheet({ activity, openReport }) {
  async function open(path, { preset = {} } = {}) {
    const node = state.nodes.get(path);
    if (!node || node.kind !== "command") return toast(`There is no tool at “${path}”.`);
    const title = titleOf(node);
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
    const specs = parameters ?? [];
    const flagged = (flag) => specs.some((spec) => spec.flags.includes(flag));
    const values = new Map(Object.entries(preset));
    const readOnly = LIVE_NAMES.has(node.name);
    // A read-only tool that only needs a pick from a short list starts on the first one, so there is something to look at straight away.
    if (readOnly) for (const spec of specs) if (spec.required && spec.control === "choice" && !spec.multiple && !values.has(spec.name)) values.set(spec.name, spec.choices[0]);
    const live = readOnly && specs.every((spec) => !spec.required || values.has(spec.name));
    const problem = h("span", { class: "tool-problem" });
    let ticket = 0;

    async function load(fresh) {
      const { tokens, problems } = form.collect();
      if (problems.length) return;
      const mine = (ticket += 1);
      resultHolder.classList.add("loading");
      if (!resultHolder.hasChildNodes()) resultHolder.replaceChildren(...skeleton(4, "row"));
      try {
        const result = await query([...pathTokens, ...tokens, ...(flagged(JSON_FLAG) ? [JSON_FLAG] : [])], fresh);
        if (mine !== ticket) return;
        resultHolder.replaceChildren(renderResult(result));
      } catch (error) {
        if (mine !== ticket) return;
        resultHolder.replaceChildren(
          notice({ glyph: "alert", tone: "bad", title: "This didn't work", body: error.message, action: button({ label: "Try again", glyph: "refresh", small: true, onclick: () => load(true) }) }),
        );
      }
      resultHolder.classList.remove("loading");
    }

    const reloadSoon = debounce(() => load(false), RELOAD_DELAY_MILLISECONDS);
    const form = createFriendlyForm({
      // Whatever the caller filled in stays in view, so a pre-filled sheet never looks empty.
      parameters: specs, values, essentials: [...(ESSENTIAL_FLAGS[path] ?? []), ...specs.filter((spec) => Object.hasOwn(preset, spec.name)).flatMap((spec) => spec.flags)],
      onChange: () => {
        const { problems } = form.collect();
        problem.textContent = problems[0] ?? "";
        primary.disabled = problems.length > 0;
        if (live) reloadSoon();
      },
    });

    async function run() {
      const { tokens, problems } = form.collect();
      if (problems.length) return;
      try {
        await activity.start({ title: fullTitleOf(node), emoji: node.icon, arguments: [...pathTokens, ...tokens], interactive: true, reveal: true });
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
          openReport({ title, blurb: friendlyText(node.summary), arguments: [...pathTokens, ...tokens.filter((token) => token !== REPORT_FLAG), REPORT_FLAG] });
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
        form.count > 0 && button({ label: "Reset", tone: "ghost", onclick: () => form.reset() }),
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
