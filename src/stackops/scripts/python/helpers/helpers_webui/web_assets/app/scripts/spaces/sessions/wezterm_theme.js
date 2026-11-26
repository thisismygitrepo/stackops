import { h, toast } from "/assets/scripts/dom.js";
import { request, state as app } from "/assets/scripts/state.js";
import { agentButton } from "../../agent_ask.js";
import { confirmAction, openSheet } from "../../overlays.js";
import { editFile } from "../../space_kit.js";
import { button, callout, copyChip, emojiTile, highlight, keyValue, notice, pathChip, pill, searchInput, sectionHead, skeleton } from "../../widgets.js";
import { plural, trailOf } from "../../words.js";
import { PICKER_COMMAND, TOOL_PATH, fileName, inUse, loss, obstacle, remarks } from "./wezterm_theme/words.js";

const STATE_ADDRESS = "/api/terminal/wezterm/state";
const APPLY_ADDRESS = "/api/terminal/wezterm/apply";
// StackOps's own WezTerm settings, by the name its list of settings files gives them.
const SETTINGS_GROUP = "wezterminal";

// The WezTerm theme sheet. A design choice, the owner's: how a terminal looks is best chosen in the terminal, where the result shows for real,
// so the command's own picker is the main way and this sheet does not try to rival it with previews. It says where things stand, starts the
// picker, and applies a theme by name for someone who already knows which one.
export function open({ activity, tools }, { preset }) {
  const node = app.nodes.get(TOOL_PATH);
  const sheet = openSheet({ label: "WezTerm theme" });
  sheet.panel.classList.add("wezterm-theme-sheet");
  const standing = h("div", { class: "wezterm-theme-standing" });
  const issues = h("div", { class: "wezterm-theme-issues" });
  const count = h("span", { class: "count" });
  const names = h("div", { class: "wezterm-theme-names" });
  // Beside controls that are greyed out, in plain sight: a hint on a button only shows under a pointer. The note above them has the reason.
  const [pickerWhy, namesWhy] = [0, 1].map(() => h("p", { class: "wezterm-theme-why", text: "Not available yet. The note above says why." }));
  // In the footer, not a toast: a toast lies over the bottom of an open sheet until it leaves.
  const said = h("span", { class: "wezterm-theme-said", role: "status" });
  const content = h("div", { class: "wezterm-theme-content" }, skeleton(4, "row"));
  let now = null;
  let term = typeof preset.theme === "string" ? preset.theme : "";
  let busy = false;

  // Both leave the sheet, because the editor and the picker open in the activity panel behind it.
  const edit = (line) => {
    sheet.close();
    editFile(activity, { title: fileName(now.path), kind: "file", path: line ? `${now.path}:${line}` : now.path });
  };
  const actions = {
    edit,
    install: () => (location.hash = "#/apps/wezterm"),
    setUp() {
      sheet.close();
      tools.open("devops config dotfiles sync", { preset: { direction: "down", which: SETTINGS_GROUP, source: "library" } });
    },
  };

  // Only asked when the theme in use is one this tool could not put back.
  const agreed = async (body, confirm) => loss(now) === "" || (await confirmAction({ title: "Replace the colour scheme?", body: `${loss(now)} ${body}`.trim(), confirm }));

  async function startPicker() {
    if (!(await agreed("The picker saves a theme as soon as you move in it.", "Start the picker"))) return;
    sheet.close();
    activity.start({ title: "WezTerm theme picker", emoji: node.icon, arguments: TOOL_PATH.split(" "), interactive: true, reveal: true }).catch((error) => toast(error.message));
  }

  async function apply(name) {
    if (busy || !(await agreed("", `Apply ${name}`))) return;
    busy = true;
    paintNames();
    try {
      now = await request("POST", APPLY_ADDRESS, { name });
      say(now.installed ? `${name} applied. Open windows change at once.` : `${name} is saved, and shows once WezTerm is installed.`, "");
    } catch (error) {
      // The file may have changed under the sheet, so where things stand is read again and the reason stays in view.
      now = await request("GET", STATE_ADDRESS).catch(() => now);
      say(error.message, "bad");
    }
    busy = false;
    paint();
  }

  function say(text, tone) {
    said.textContent = text;
    said.className = `wezterm-theme-said ${tone}`;
  }

  function paintNames() {
    const wanted = term.trim().toLowerCase();
    const sorted = [...now.names].sort((left, right) => left.localeCompare(right, undefined, { sensitivity: "base" }));
    const shown = sorted.filter((name) => name.toLowerCase().includes(wanted));
    const reason = obstacle(now);
    count.textContent = wanted ? `${shown.length} of ${plural(now.names.length, "theme")}` : plural(now.names.length, "theme");
    names.replaceChildren(
      ...shown.map((name) => {
        const applyButton = button({ label: "Apply", small: true, title: reason || `Use ${name} in WezTerm`, onclick: () => apply(name) });
        applyButton.disabled = busy || reason !== "";
        const inUseNow = now.file === "ready" && name === now.current;
        return h("div", { class: "wezterm-theme-name", "aria-current": inUseNow && "true" }, h("span", {}, highlight(name, term.trim())), inUseNow ? pill("In use", "good") : applyButton);
      }),
    );
    if (shown.length === 0) names.replaceChildren(h("p", { class: "wezterm-theme-none", text: "No theme has that in its name." }));
  }

  function paint() {
    const reason = !now.installed ? "WezTerm is not installed, so there is no window to show the themes on." : obstacle(now);
    const { text, note } = inUse(now);
    standing.replaceChildren(
      keyValue([
        ["WezTerm", pill(now.installed ? "Installed" : "Not installed", now.installed ? "good" : "warn")],
        ["Theme in use", h("span", {}, h("strong", { text }), note && h("span", { class: "dim", text: ` ${note}` }))],
        ["Settings file", pathChip(now.path)],
      ]),
    );
    issues.replaceChildren(
      ...remarks(now, actions).map(({ action, snippet, ...remark }) =>
        callout({ ...remark, extra: [snippet && copyChip(snippet), action && button({ label: action.label, glyph: action.glyph, small: true, onclick: action.onclick })] }),
      ),
    );
    pickerButton.disabled = reason !== "";
    pickerButton.title = reason || "Runs the picker in the activity panel of this app";
    pickerWhy.hidden = reason === "";
    namesWhy.hidden = obstacle(now) === "";
    paintNames();
  }

  async function load() {
    content.replaceChildren(...skeleton(4, "row"));
    try {
      now = await request("GET", STATE_ADDRESS);
    } catch (error) {
      content.replaceChildren(notice({ glyph: "alert", tone: "bad", title: "WezTerm's settings could not be read", body: error.message, action: button({ label: "Try again", glyph: "refresh", small: true, onclick: load }) }));
      return;
    }
    content.replaceChildren(standing, issues, pickerSection, nameSection);
    paint();
  }

  const pickerButton = button({ label: "Start the picker here", glyph: "play", tone: "primary", onclick: startPicker });
  const pickerSection = h(
    "section",
    { class: "wezterm-theme-way" },
    sectionHead("Choose in a terminal"),
    h("p", { text: "The best way to choose a theme is the picker in a terminal. It puts each theme on your real WezTerm windows as you move through the names, so it only makes sense with a WezTerm window open and in view." }),
    h("p", { class: "dim", text: "The arrow keys move, and each move saves that theme. Enter closes the picker." }),
    h("div", { class: "wezterm-theme-start" }, copyChip(PICKER_COMMAND), pickerButton, pickerWhy),
  );
  const search = searchInput({
    placeholder: "Find a theme by name",
    oninput: (value) => {
      term = value;
      paintNames();
    },
  });
  search.input.value = term;
  const nameSection = h(
    "section",
    { class: "wezterm-theme-way" },
    sectionHead("Or pick by name"),
    h("p", { text: "For when you already know which theme you want. There are no previews here." }),
    h("div", { class: "wezterm-theme-find" }, search.element, count),
    namesWhy,
    names,
  );

  sheet.body.append(
    h("header", { class: "tool-head" }, emojiTile(node.icon || "🎨", node.path, 56), h("div", {}, h("span", { class: "overline", text: trailOf(node) || "StackOps" }), h("h1", { text: "WezTerm theme" }), h("p", { text: "The colours of your WezTerm windows." }))),
    content,
  );
  sheet.foot.hidden = false;
  sheet.foot.append(
    agentButton(activity, { commands: [TOOL_PATH] }),
    button({
      label: "All options", glyph: "sliders", tone: "ghost", title: "This tool's own form, with every option the command has",
      onclick: () => {
        sheet.close();
        tools.open(TOOL_PATH, { preset, plain: true });
      },
    }),
    said,
  );
  return load();
}
