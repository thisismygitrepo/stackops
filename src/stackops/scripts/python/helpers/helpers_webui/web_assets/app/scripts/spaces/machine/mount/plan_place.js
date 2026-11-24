import { h } from "/assets/scripts/dom.js";
import { segmented } from "../../../widgets.js";
import { createPlaceField } from "./place_field.js";

const PLACE_MODES = [["usual", "Where macOS puts it"], ["folder", "A folder I choose"]];

// The second step: where the device should appear. macOS has a place of its own and takes a folder instead; Linux takes a folder, and the
// view suggests one; Windows takes a drive letter. A way that picks the place itself leaves nothing to choose.
// `paint(plan)` shows what fits the way in use. The folder box is made once and kept, so typing in it is never interrupted.
export function createWhere({ picture, device, choice, changed }) {
  const { system } = picture;
  let field = null;
  const fieldHolder = h("div");
  const usual = h("p", { class: "mount-where-note" }, device.name ? ["macOS chooses the place, which is usually ", h("code", { text: `/Volumes/${device.name}` })] : ["macOS chooses the place, a folder under ", h("code", { text: "/Volumes" })]);
  const systemChooses = h("p", { class: "mount-where-note", text: "The system chooses the place, under /run/media or /media. The list shows it once the device is mounted." });
  const mode =
    system === "Darwin" &&
    segmented(PLACE_MODES, (id) => {
      choice.place = id;
      changed();
      if (id === "folder") field.input.focus();
    });
  const letters =
    system === "Windows" &&
    h(
      "div",
      { class: "chip-row" },
      picture.letters.map((letter) =>
        h("button", {
          class: "chip-button mount-letter", type: "button", text: `${letter}:`, "data-letter": letter,
          onclick: () => {
            choice.letter = letter;
            changed();
          },
        }),
      ),
    );
  const noLetters = system === "Windows" && picture.letters.length === 0 && h("p", { class: "mount-where-note", text: "Every drive letter is taken. Free one, then refresh." });

  function paint(plan) {
    const typed = plan.way.places && system !== "Windows" && choice.place === "folder";
    systemChooses.hidden = plan.way.places;
    usual.hidden = !(plan.way.places && system === "Darwin" && choice.place === "usual");
    if (mode) {
      mode.element.hidden = !plan.way.places;
      mode.set(choice.place);
    }
    if (letters) for (const chip of letters.children) chip.setAttribute("aria-pressed", String(chip.dataset.letter === choice.letter));
    fieldHolder.hidden = !typed;
    if (!typed || field) return;
    field = createPlaceField({
      kind: "folder", label: "Folder to mount at", placeholder: "Type a folder, for example ~/mnt/photos", value: choice.folder,
      hint: system === "Linux" ? "Type the folder it should appear as, for example /mnt/photos." : "Type the folder it should appear as, or pick one from the suggestions.",
      onChange(text, check) {
        choice.folder = text;
        choice.folderCheck = check;
        changed();
      },
    });
    fieldHolder.append(field.element);
  }

  return { element: h("div", { class: "mount-where" }, mode && mode.element, letters, noLetters, usual, fieldHolder, systemChooses), paint };
}
