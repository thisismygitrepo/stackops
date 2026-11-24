import { h, icon } from "/assets/scripts/dom.js";
import { pill } from "../../../widgets.js";
import { createPlaceField } from "./place_field.js";
import { WAYS, WAY_BLOCKS, wayBlurb } from "./words.js";

// What sits under "More options": the command's three ways of mounting, with the one chosen for this device marked and the ones that cannot
// work here greyed out with the reason, the key file for a way that takes one, and the way to the command's own form.
export function createMore({ picture, device, choice, changed, openForm }) {
  const { system } = picture;
  const ways = device.ways.map((way) => {
    const row = h(
      "button",
      {
        class: "mount-way", type: "button", role: "radio", disabled: !way.usable,
        onclick: () => {
          choice.backend = way.backend === device.backend ? "" : way.backend;
          changed();
        },
      },
      h("i", { class: "mount-dot" }),
      h("span", { class: "mount-way-text" }, h("strong", { text: WAYS[way.backend].title }), h("span", { text: way.usable ? wayBlurb(way.backend, system) : WAY_BLOCKS[way.why](way.backend) })),
      way.backend === device.backend && pill("Chosen for you", "accent"),
    );
    return { way, row };
  });
  let keyField = null;
  const keyHolder = h("div");
  const keyOff = h("p", { class: "mount-where-note", text: system === "Linux" ? "A key file only applies to encrypted devices." : "A key file only applies to encrypted devices on Linux." });
  const toggle = h("button", { class: "more-toggle", type: "button", "aria-expanded": "false" }, icon("sliders", 15), h("span", { text: "More options" }), icon("down", 14));
  const drawer = h(
    "div",
    { class: "more-body" },
    h(
      "div",
      { class: "fields" },
      h("div", { class: "field" }, h("span", { class: "field-label" }, h("span", { text: "How it is mounted" })), h("div", { class: "mount-ways", role: "radiogroup", "aria-label": "How it is mounted" }, ways.map((item) => item.row))),
      h("div", { class: "field" }, h("span", { class: "field-label" }, h("span", { text: "Key file" })), keyHolder, keyOff),
      h("p", { class: "mount-where-note" }, "Anything else the command can do is in ", h("button", { class: "link", type: "button", text: "its own form", onclick: openForm }), "."),
    ),
  );
  const setOpen = (open) => {
    toggle.setAttribute("aria-expanded", String(open));
    drawer.classList.toggle("open", open);
    // A closed drawer is only folded away, so its controls are also taken out of reach of the keyboard.
    drawer.inert = !open;
  };
  toggle.addEventListener("click", () => setOpen(toggle.getAttribute("aria-expanded") !== "true"));
  // What the view was opened with is never tucked away.
  setOpen(choice.backend !== "" || choice.keyFile !== "");

  function paint(plan) {
    for (const { way, row } of ways) row.setAttribute("aria-checked", String(way === plan.way));
    keyHolder.hidden = !plan.way.takes_key;
    keyOff.hidden = plan.way.takes_key;
    if (!plan.way.takes_key || keyField) return;
    keyField = createPlaceField({
      kind: "key", label: "Key file", placeholder: "Type the path of the key file", value: choice.keyFile,
      hint: "A recovery key or key file that unlocks the device. Leave it empty to type the password in the Activity panel.",
      onChange(text, check) {
        choice.keyFile = text;
        choice.keyCheck = check;
        changed();
      },
    });
    keyHolder.append(keyField.element);
  }

  return { element: h("div", { class: "mount-more" }, toggle, drawer), paint };
}
