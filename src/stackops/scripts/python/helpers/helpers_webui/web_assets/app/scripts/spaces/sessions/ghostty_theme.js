import { h, icon } from "/assets/scripts/dom.js";
import { request, state } from "/assets/scripts/state.js";
import { capture, query } from "../../data.js";
import { openSheet } from "../../overlays.js";
import { button, copyChip, emojiTile, notice, pathChip, sectionHead, skeleton } from "../../widgets.js";
import { friendlyText, titleOf, trailOf } from "../../words.js";
import { createPickList } from "./ghostty_theme/pick_list.js";
import { statusFailure, statusView } from "./ghostty_theme/status_view.js";
import { STATUS_ADDRESS, TOOL_COMMAND, TOOL_PATH, TOOL_TOKENS, isSingle, isUnset, reloadKeys, sameAs, themeWords } from "./ghostty_theme/words.js";

const NOT_READY = {
  missing: { reason: "Ghostty is not installed.", names: "The names come from Ghostty's own list, so they show here once Ghostty is installed." },
  unreachable: { reason: "Ghostty cannot be run from here.", names: "The names come from Ghostty's own list, so they show here once StackOps can run Ghostty." },
};

// A small sheet for `devops config terminal ghostty-theme`. Design choice: it does not preview themes. A terminal's colours are best judged in a
// terminal, and Ghostty's own picker does that, so the sheet leads there: the command to copy, and a button that runs the same picker in the
// activity panel. For someone who already knows the name there is a plain list with Apply.
// The list and Apply go through the command itself; only whether Ghostty is here and the theme it is set to use come from the server's own route.
export function open({ activity, tools }, { preset = {} }) {
  const node = state.nodes.get(TOOL_PATH);
  const sheet = openSheet({ label: titleOf(node) });
  const statusHolder = h("div", { class: "ghostty-theme-status" }, skeleton(1, "row"));
  const pickHolder = h("div", { class: "ghostty-theme-pick-holder" });
  const outcome = h("div", { class: "ghostty-theme-outcome", role: "status", hidden: true });
  const reason = h("span", { class: "ghostty-theme-reason" });
  const pickerButton = button({ label: "Open the picker", glyph: "play", tone: "primary", title: "Starts Ghostty's theme picker in the activity panel", onclick: startPicker });
  pickerButton.disabled = true;
  let status = null;
  let picks = null;
  let names = [];
  let alive = true;
  let launching = false;
  let applying = false;
  sheet.closed.then(() => (alive = false));

  const inUse = () => new Set(status.theme ? [status.theme.light, status.theme.dark].filter(Boolean) : []);

  // One start per sheet: a second press lands while the first is on its way, and on the button as the sheet slides out.
  async function startPicker() {
    if (launching) return;
    launching = true;
    try {
      await activity.start({ title: "Ghostty theme picker", emoji: node.icon, arguments: TOOL_TOKENS, interactive: true, reveal: true });
      sheet.close();
    } catch (error) {
      launching = false;
      reason.classList.add("bad");
      reason.textContent = error.message;
    }
  }

  function say(tone, ...parts) {
    outcome.className = `ghostty-theme-outcome ${tone}`;
    outcome.hidden = false;
    outcome.replaceChildren(icon(tone === "good" ? "check" : "alert", 16), h("div", {}, parts));
  }

  // What Ghostty reports after the change is what the sheet goes by: a Ghostty that reads its settings from another file would not pick the theme up.
  async function apply(name) {
    if (applying) return;
    applying = true;
    const before = status.theme;
    let receipt;
    try {
      receipt = (await capture([...TOOL_TOKENS, `--theme=${name}`, "--json"])).json;
      if (!receipt?.applied) throw new Error("The command did not confirm the change.");
    } catch (error) {
      applying = false;
      if (alive) say("bad", h("p", {}, h("strong", { text: name }), ` was not set. ${friendlyText(error.message)}`));
      return;
    }
    // The theme is saved by now. If Ghostty cannot be asked again, the sheet stops saying which theme is in use.
    status = await request("GET", STATUS_ADDRESS).catch(() => ({ ...status, theme: null }));
    applying = false;
    if (!alive) return;
    statusHolder.replaceChildren(statusView(status));
    picks.mark(inUse());
    const took = !status.theme || sameAs(status.theme, name);
    const changed = before && !sameAs(before, name);
    const undo = changed && isSingle(before) && names.includes(before.light) && button({ label: `Put ${before.light} back`, small: true, onclick: () => apply(before.light) });
    say(
      took ? "good" : "warn",
      took
        ? h("p", {}, h("strong", { text: name }), " is saved. To load it in the Ghostty windows you have open, press ", reloadKeys(), " there.")
        : h("p", {}, h("strong", { text: name }), ` is saved, but Ghostty still reports ${themeWords(status.theme)}. It may be reading its settings from another file.`),
      changed && h("p", { class: "dim", text: isUnset(before) ? "No theme was set before." : `Before this it was ${themeWords(before)}.` }),
      receipt.paths?.[1] && h("p", { class: "dim" }, "Kept in ", pathChip(receipt.paths[1])),
      undo,
    );
  }

  async function loadNames(fresh) {
    pickHolder.replaceChildren(...skeleton(4, "row"));
    try {
      names = (await query([...TOOL_TOKENS, "--list", "--json"], fresh)).json.themes;
    } catch (error) {
      if (alive) pickHolder.replaceChildren(notice({ glyph: "alert", tone: "bad", title: "The list of themes did not load", body: friendlyText(error.message), action: button({ label: "Try again", glyph: "refresh", small: true, onclick: () => loadNames(true) }) }));
      return;
    }
    if (!alive) return;
    picks = createPickList({ names, term: typeof preset.theme === "string" ? preset.theme : "", onApply: apply });
    picks.mark(inUse());
    pickHolder.replaceChildren(picks.element);
  }

  async function load() {
    statusHolder.replaceChildren(...skeleton(1, "row"));
    try {
      status = await request("GET", STATUS_ADDRESS);
    } catch (error) {
      if (!alive) return;
      statusHolder.replaceChildren(statusFailure(error, load));
      reason.textContent = "Could not check for Ghostty.";
      pickHolder.replaceChildren(h("p", { class: "dim", text: "The names show here once StackOps can check for Ghostty." }));
      return;
    }
    if (!alive) return;
    const ready = status.state === "ready";
    statusHolder.replaceChildren(statusView(status));
    pickerButton.disabled = !ready;
    reason.textContent = ready ? "" : NOT_READY[status.state].reason;
    if (ready) loadNames(false);
    else pickHolder.replaceChildren(h("p", { class: "dim", text: NOT_READY[status.state].names }));
  }

  sheet.body.append(
    h("header", { class: "tool-head" }, emojiTile(node.icon || "👻", node.path, 56), h("div", {}, h("span", { class: "overline", text: trailOf(node) || "StackOps" }), h("h1", { text: titleOf(node) }), h("p", { text: "Choose the colours Ghostty uses." }))),
    statusHolder,
    h(
      "section",
      { class: "ghostty-theme-part" },
      sectionHead("Choose in a terminal"),
      h("p", { text: "The best place to choose a terminal's colours is a terminal. Ghostty's own picker shows each theme in its real colours as you move through the list." }),
      h("div", { class: "ghostty-theme-command" }, copyChip(TOOL_COMMAND)),
      h("p", { text: "Run that in a terminal, or open the picker here with the button at the bottom. Move with the arrow keys, press Enter on a theme, then w to save it." }),
      h("p", { class: "ghostty-theme-note" }, "Ghostty loads a saved theme the next time it starts. To load it in the windows you have open, press ", reloadKeys(), " in Ghostty."),
    ),
    h("section", { class: "ghostty-theme-part" }, sectionHead("Or set one by name"), h("p", { text: "For when you already know the theme's name. There is no preview here." }), pickHolder, outcome),
  );
  sheet.foot.hidden = false;
  sheet.foot.append(
    button({
      label: "All options", glyph: "sliders", tone: "ghost", title: "This tool's own form, with every option the command has",
      onclick: () => {
        sheet.close();
        tools.open(TOOL_PATH, { preset, plain: true });
      },
    }),
    reason,
    pickerButton,
  );
  load();
}
