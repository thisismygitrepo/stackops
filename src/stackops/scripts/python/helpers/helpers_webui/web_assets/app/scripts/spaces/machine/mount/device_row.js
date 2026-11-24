import { h } from "/assets/scripts/dom.js";
import { glyphTile, highlight, pathChip, pill } from "../../../widgets.js";
import { sittingOf, titleOf } from "./model.js";
import { STATES, STUCK, blockText, fileSystemName, isStuck, sizeText } from "./words.js";

const glyphOf = (device) => (device.encryption ? "lock" : device.block === "apfs_container" ? "layers" : device.kind === "disk" ? "server" : "database");

// The device's disk as a bar, cut where its parts are, with this one lit.
function diskMap(sitting) {
  return h("span", { class: "mount-map", title: sitting.text, "aria-hidden": "true" }, sitting.shares.map(({ share, own }) => h("i", { class: own ? "own" : "", style: `flex-grow:${Math.max(share, 0.03)}` })));
}

// One device of the list. Only one that can be mounted is a control; the others say where they are mounted, or why they cannot be.
export function deviceRow({ device, picture, picked, term, onPick }) {
  const state = STATES[device.state];
  const mark = isStuck(device) ? STUCK : state;
  const sitting = sittingOf(picture.devices, device);
  const facts = [fileSystemName(device), device.name && device.key, sitting.text].filter(Boolean).join(" · ");
  const parts = [
    h("i", { class: "mount-dot" }),
    glyphTile(glyphOf(device), state.hue, 38),
    h(
      "span",
      { class: "mount-text" },
      h("strong", {}, highlight(titleOf(device), term)),
      h("span", { text: facts }),
      device.state === "blocked" && h("small", { text: blockText(device, picture.system) }),
      device.state === "mounted" && h("span", { class: "mount-at" }, "at", pathChip(device.mounted_at)),
    ),
    diskMap(sitting),
    h("strong", { class: "mount-size num", text: sizeText(device) || "—" }),
    h("span", { class: "mount-state" }, pill(mark.label, mark.tone)),
  ];
  if (device.state !== "ready") return h("li", { class: `mount-row ${device.state}${isStuck(device) ? " stuck" : ""}`, "data-key": device.key }, h("div", { class: "mount-row-main" }, parts));
  return h(
    "li",
    { class: `mount-row ready${picked ? " picked" : ""}`, "data-key": device.key },
    h("button", { class: "mount-row-main", type: "button", "aria-pressed": String(picked), onclick: () => onPick(device) }, parts),
  );
}
