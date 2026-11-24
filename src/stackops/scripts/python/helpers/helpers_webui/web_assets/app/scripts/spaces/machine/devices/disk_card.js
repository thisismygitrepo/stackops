import { h, icon } from "/assets/scripts/dom.js";
import { button, glyphTile, pathChip, pill } from "../../../widgets.js";
import { freeOn, slotsOf } from "./model.js";
import { spaceMap } from "./space_map.js";
import { volumeRow } from "./volume_row.js";
import { PLACES, RANKED_TITLES, connectionOf, partsLine, size } from "./words.js";

const TAGS = { internal: "Internal", external: "External", image: "Disk image" };
const HEALTH = {
  good: ["check", "Healthy", "good", "The disk's own self-check reports no problem"],
  failing: ["alert", "Failing", "bad", "The disk's own self-check reports that it is failing. Copy what matters off it."],
};

function card(key, head, body) {
  return h("section", { class: "devices-disk", "data-disk": key }, head, body);
}

function rowList(rows, options, slots) {
  return h("ul", { class: "devices-rows" }, rows.map((row) => volumeRow(row, { ...options, slot: slots?.get(row.volume.id) })));
}

// The system parts a disk keeps out of the list, as one line that brings them into it.
function partsFold(group, { handlers }) {
  const parts = group.volumes.filter((volume) => volume.helper);
  const bytes = parts.reduce((sum, volume) => sum + (volume.pool === "" ? volume.size : (volume.used ?? 0)), 0);
  return h(
    "button",
    { class: "devices-fold", type: "button", "data-key": "parts", title: "What the system keeps on this disk for itself: start-up files, recovery, extra memory", onclick: handlers.showParts },
    h("i", { class: "devices-dot", "data-slot": "quiet" }),
    h("span", { text: partsLine(parts.length, bytes) }),
    h("em", {}, "Show them", icon("down", 13)),
  );
}

// One disk: what it is, a bar of everything on it from end to end, then its volumes. Pointing at a stretch of the bar lights the row it
// stands for, and pointing at a row lights its stretch.
export function diskCard(group, rows, options) {
  const { disk } = group;
  const { view, handlers } = options;
  const slots = slotsOf(disk);
  const free = freeOn(disk);
  const health = HEALTH[disk.health];
  const eject = disk.can_eject && (view.busy.has(disk.id) ? h("span", { class: "devices-busy" }, h("i", { class: "ring" })) : button({ label: "Eject", glyph: "up", small: true, title: disk.place === "image" ? "Close this disk image" : "Unmount everything on it so it can be unplugged", onclick: () => handlers.eject(group) }));
  const head = h(
    "header",
    { class: "devices-disk-head" },
    glyphTile(PLACES[disk.place].glyph, PLACES[disk.place].hue, 44),
    h(
      "div",
      { class: "devices-disk-text" },
      h("h2", { text: group.title }),
      h(
        "p",
        {},
        pill(TAGS[disk.place], disk.place === "internal" ? "" : "accent"),
        disk.place === "external" && connectionOf(disk) && pill(connectionOf(disk)),
        disk.removable && pill("Removable"),
        disk.solid_state && pill("Solid state"),
        health && h("span", { class: `pill ${health[2]}`, title: health[3] }, icon(health[0], 12), health[1]),
        disk.image_file && pathChip(disk.image_file),
      ),
    ),
    h("div", { class: "devices-disk-sum" }, h("strong", { class: "num", text: free === null ? size(disk.size) : `${size(free)} free` }), h("span", { text: free === null ? "in all" : `of ${size(disk.size)}` })),
    eject,
  );
  const hiddenParts = !view.parts && view.term.trim() === "" && group.volumes.some((volume) => volume.helper);
  const element = card(disk.id, head, [spaceMap(disk, point), rowList(rows, options, slots), hiddenParts && partsFold(group, options)]);
  function point(key) {
    for (const pointed of element.querySelectorAll(".devices-pointed")) pointed.classList.remove("devices-pointed");
    if (key) for (const match of element.querySelectorAll(`[data-key="${CSS.escape(key)}"]`)) match.classList.add("devices-pointed");
  }
  element.addEventListener("pointerover", (event) => {
    const row = event.target.closest(".devices-row, .devices-fold");
    if (row) point(row.dataset.key);
  });
  element.addEventListener("pointerleave", () => point(null));
  return element;
}

export function sharesCard(group, rows, options) {
  const head = h(
    "header",
    { class: "devices-disk-head" },
    glyphTile(PLACES.network.glyph, PLACES.network.hue, 44),
    h("div", { class: "devices-disk-text" }, h("h2", { text: group.title }), h("p", {}, h("span", { class: "dim", text: "Folders on other computers that are mounted here." }))),
    h("div", { class: "devices-disk-sum" }, h("strong", { class: "num", text: String(group.volumes.length) }), h("span", { text: group.volumes.length === 1 ? "share" : "shares" })),
  );
  return card(group.id, head, rowList(rows, options, null));
}

// Every volume in one list, whichever disk it is on, in the order asked for.
export function rankedCard(rows, options) {
  const head = h(
    "header",
    { class: "devices-disk-head" },
    glyphTile("chart", 252, 44),
    h("div", { class: "devices-disk-text" }, h("h2", { text: RANKED_TITLES[options.view.order] }), h("p", {}, h("span", { class: "dim", text: "Whichever disk it is on." }))),
    h("div", { class: "devices-disk-sum" }, h("strong", { class: "num", text: String(rows.length) }), h("span", { text: rows.length === 1 ? "volume" : "volumes" })),
  );
  return card("ranked", head, rowList(rows, { ...options, ranked: true }, null));
}
