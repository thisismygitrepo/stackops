import { h, icon, tildify, toast } from "/assets/scripts/dom.js";
import { request, state } from "/assets/scripts/state.js";
import { agentButton } from "../../agent_ask.js";
import { openSheet } from "../../overlays.js";
import { button, copyChip, emojiTile, keyValue, notice, pathChip, pill, sectionHead, skeleton } from "../../widgets.js";
import { titleOf, trailOf } from "../../words.js";
import { createByName } from "./starship_theme/by_name.js";

const PATH = "devops config terminal starship-theme";
const TOKENS = PATH.split(" ");
const COMMAND = `stackops ${PATH}`;

// What the settings file holds now, and a line under it.
const IN_USE = {
  standard: () => ["Starship's standard look", "The settings file is missing or empty."],
  preset: (found) => [`The ${found.preset} preset`, "Exactly as Starship ships it."],
  own: () => ["Your own settings", "The file matches none of the presets."],
  unreadable: (found) => ["Unknown", `The settings file could not be read. ${found.problem}.`],
};

// A small sheet on purpose. A prompt is best chosen in a terminal, where the picker draws it for real, so this says what is in use, sends the
// person to that picker, and applies a preset by name for someone who already knows which one. It draws no previews of its own.
export function open({ activity, tools }, { preset = {} }) {
  const node = state.nodes.get(PATH);
  const title = titleOf(node);
  const sheet = openSheet({ label: title });
  const content = h("div", { class: "starship-content" }, skeleton(3, "row"));
  const shown = (path) => tildify(path, state.boot.home);
  let showing = true;

  // The sheet closes before anything starts in the activity panel: while a sheet is open, the page behind it, the panel included, takes no keys.
  function run(task) {
    sheet.close();
    activity.start({ ...task, interactive: true, reveal: true }).catch((error) => toast(error.message));
  }

  function picker(found) {
    const tool = found.picker_tool !== "";
    const blocked = !tool
      ? "The picker shows its list with fzf or television, and neither is installed."
      : found.picker_elsewhere && `The picker always writes ${shown(found.picker_elsewhere)}, but Starship here reads ${shown(found.settings_path)}, so its choice would not show. Pick by name below.`;
    const start = button({
      label: "Open the picker here", glyph: "terminal", tone: "primary", title: blocked || "Runs the picker in the activity panel",
      onclick: () => run({ title: "Choose a Starship preset", emoji: node.icon || "🌟", arguments: TOKENS, wide: true }),
    });
    start.disabled = Boolean(blocked);
    return h(
      "section",
      { class: "starship-section" },
      sectionHead("Choose in a terminal"),
      h("p", { text: "The best way to choose a look is the picker in your own terminal. It draws each preset there, in your terminal's font and colours, and applies the one you pick." }),
      !blocked && h("div", { class: "starship-command" }, h("span", { text: "Run this in a terminal" }), copyChip(COMMAND)),
      h(
        "div",
        { class: "starship-run" },
        start,
        !tool && button({ label: "Install fzf", glyph: "download", onclick: () => run({ title: "Install fzf", emoji: "📦", arguments: ["devops", "software", "install", "fzf"] }) }),
      ),
      blocked
        ? h("p", { class: "starship-reason" }, icon("alert", 15), h("span", { text: blocked }))
        : h("p", { class: "starship-hint", text: `The same picker, in the activity panel. The panel has a font of its own, so symbols that need a Nerd Font show as boxes there. Enter applies the highlighted preset${found.kind === "own" ? " and replaces your own settings" : ""}. Escape leaves everything as it is.` }),
    );
  }

  function paint(found) {
    // A box that is taken off the page while it has the focus does not always say so, and its list of suggestions would stay behind.
    if (content.contains(document.activeElement)) document.activeElement.blur();
    if (!found.installed) {
      content.replaceChildren(
        notice({
          glyph: "download", title: "Starship is not installed", body: "Starship is the program that draws the prompt. Once it is installed, open this again to choose a look.",
          action: button({ label: "Install Starship", glyph: "download", tone: "primary", onclick: () => run({ title: "Install Starship", emoji: "📦", arguments: ["devops", "software", "install", "starship"] }) }),
        }),
      );
      return;
    }
    const [what, note] = IN_USE[found.kind](found);
    content.replaceChildren(
      h(
        "div",
        { class: "starship-state" },
        keyValue([
          ["Starship", h("span", { class: "starship-fact" }, h("span", { text: `Version ${found.version}` }), pill("Installed", "good"))],
          ["In use now", h("span", { class: "starship-fact" }, h("strong", { text: what }), h("small", { text: note }))],
          ["Settings file", pathChip(found.settings_path)],
        ]),
      ),
      picker(found),
      createByName({ tokens: TOKENS, found, shown, wanted: preset.theme, onApplied: load }),
    );
  }

  async function load() {
    try {
      const found = await request("GET", "/api/terminal/starship/state");
      if (showing) paint(found);
    } catch (error) {
      if (showing) content.replaceChildren(notice({ glyph: "alert", tone: "bad", title: "This didn't load", body: error.message, action: button({ label: "Try again", glyph: "refresh", small: true, onclick: load }) }));
    }
  }

  sheet.body.append(
    h(
      "header",
      { class: "tool-head" },
      emojiTile(node.icon || "🌟", node.path, 56),
      h("div", {}, h("span", { class: "overline", text: trailOf(node) || "StackOps" }), h("h1", { text: title }), h("p", { text: "Starship draws the prompt, the line your terminal shows before each command." })),
    ),
    content,
  );
  sheet.foot.hidden = false;
  sheet.foot.append(
    agentButton(activity, { commands: [PATH] }),
    button({
      label: "All options", glyph: "sliders", tone: "ghost", title: "The tool's own form, with every option it has",
      onclick: () => {
        sheet.close();
        tools.open(PATH, { preset, plain: true });
      },
    }),
  );
  sheet.closed.then(() => (showing = false));
  return load();
}
