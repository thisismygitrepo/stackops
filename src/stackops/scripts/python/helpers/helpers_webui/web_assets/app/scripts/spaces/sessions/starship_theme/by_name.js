import { h, icon, toast } from "/assets/scripts/dom.js";
import { createCombo } from "../../../combo.js";
import { capture, markStale, query } from "../../../data.js";
import { confirmAction } from "../../../overlays.js";
import { button, notice, pill, sectionHead, skeleton } from "../../../widgets.js";

const PRESETS_PAGE = "https://starship.rs/presets/";

// One sentence on what applying costs, by what the settings file holds now.
const LOSS = {
  standard: (file) => `This creates the settings file ${file}.`,
  preset: (file, found) => `This replaces everything in ${file}, which now holds the ${found.preset} preset.`,
  own: (file) => `This replaces everything in ${file}, and your own settings there are gone for good.`,
  unreadable: (file) => `This replaces everything in ${file}, which could not be read just now.`,
};

// Picking a preset by its name, for someone who already knows which one: the command's own list to search, and Apply. No preview on purpose;
// the picker in a terminal is where a look is judged. `found` is the state the sheet read, `shown` writes a path the short way, and `onApplied`
// is called once the settings file holds the new preset.
export function createByName({ tokens, found, shown, wanted, onApplied }) {
  const holder = h("div", { class: "starship-pick" }, skeleton(1, "row"));
  const problem = h("p", { class: "starship-reason bad", hidden: true });
  const elsewhere = found.by_name_elsewhere;

  async function build() {
    let names;
    try {
      names = (await query([...tokens, "--list", "--json"])).json.themes;
    } catch (error) {
      holder.replaceChildren(notice({ glyph: "alert", tone: "bad", title: "The presets could not be listed", body: error.message, action: button({ label: "Try again", glyph: "refresh", small: true, onclick: build }) }));
      return;
    }
    const typed = () => combo.input.value.trim();
    const ready = () => names.includes(typed()) && typed() !== found.preset && !elsewhere;
    const sync = () => (applyButton.disabled = !ready());

    async function apply() {
      const name = typed();
      if (!ready()) return;
      // The dialog is narrow and a path has no spaces, so it is given places to break: without them a long one pushes the buttons out of the dialog.
      const file = shown(found.settings_path).replace(/[\\/]/g, "$&\u200b");
      const sure = await confirmAction({ title: `Use ${name}?`, body: LOSS[found.kind](file, found), confirm: "Apply", tone: found.kind === "own" ? "danger" : "primary" });
      if (!sure) return;
      applyButton.disabled = true;
      problem.hidden = true;
      try {
        const { json } = await capture([...tokens, "--theme", name, "--json"]);
        if (!json?.applied) throw new Error("The command ended without saying that the preset is in place.");
        markStale();
        toast(`${name} is in place. Your terminal shows it from its next prompt line.`, "info");
        onApplied();
      } catch (error) {
        problem.replaceChildren(icon("alert", 15), h("span", { text: `That did not work. ${error.message}` }));
        problem.hidden = false;
        sync();
      }
    }

    const combo = createCombo({
      value: names.includes(wanted) ? wanted : "", placeholder: "Find a preset by name", glyph: "search", label: "Preset name", emptyText: "No preset has that name",
      suggest: async (term) => names.filter((name) => name.includes(term.trim().toLowerCase())).map((name) => ({ value: name, trail: name === found.preset && pill("In use", "good") })),
      onInput: sync, onPick: () => sync(),
    });
    const applyButton = button({ label: "Apply", glyph: "check", title: elsewhere ? "Starship would not read the file this writes" : "Replaces the settings file with this preset", onclick: apply });
    // The list takes Enter for itself while a suggestion is marked; once the box holds a preset's name, Enter applies it.
    combo.input.addEventListener("keydown", (event) => event.key === "Enter" && !event.defaultPrevented && apply());
    sync();
    holder.replaceChildren(combo.element, applyButton);
  }

  build();
  return h(
    "section",
    { class: "starship-section" },
    sectionHead("Already know the name?"),
    h(
      "p",
      {},
      "Pick a preset by name and it is applied as it is, without a preview. ",
      h("a", { class: "link", href: PRESETS_PAGE, target: "_blank", rel: "noopener noreferrer", title: "Opens Starship's own page of presets" }, "Starship's website shows each one", icon("external", 12)),
      ".",
    ),
    holder,
    elsewhere && h("p", { class: "starship-reason" }, icon("alert", 15), h("span", { text: `Picking by name writes ${shown(elsewhere)}, but Starship here reads ${shown(found.settings_path)}, so the choice would not show. Use the picker.` })),
    problem,
  );
}
