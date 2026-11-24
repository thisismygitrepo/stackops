import { h, icon } from "/assets/scripts/dom.js";
import { CLEANUP_HASH } from "../../../disk_cleanup_words.js";
import { button, copyChip, iconButton, keyValue, pathChip, pill } from "../../../widgets.js";
import { fullness, handsOver, isMounted, pressureOf, sharingOf } from "./model.js";
import { PLACES, formatOf, roleOf, size, spaceSentence, volumeName, whyNoMount } from "./words.js";

const PRESSURE = { bad: "Almost full", warn: "Getting full" };
const flag = (glyph, text, tone, title) => h("span", { class: `pill ${tone}`, title }, icon(glyph, 12), text);

function usage(volume, pressure) {
  const full = fullness(volume);
  if (!full) return h("div", { class: "devices-usage" }, h("span", { class: "devices-figure" }, volume.size > 0 && h("strong", { class: "num", text: size(volume.size) }), h("span", { class: "dim", text: isMounted(volume) ? "" : "not mounted" })));
  const title = `${size(volume.used)} here${full.others > 0 ? ` · ${size(volume.size - volume.used - volume.free)} in other volumes` : ""} · ${size(volume.free)} free`;
  return h(
    "div",
    { class: `devices-usage ${pressure}` },
    h("span", { class: "devices-meter", title }, h("i", { class: "own", style: `--share:${full.own}` }), full.others > 0 && h("i", { class: "others", style: `--share:${full.others}` })),
    h("span", { class: "devices-figure" }, h("strong", { class: "num", text: `${size(volume.used)} used` }), h("span", { class: "dim", text: `${size(volume.free)} free` })),
  );
}

// The one thing to do with a volume from its row: mount it when it is not mounted, unmount it when this page may. A volume that cannot be
// mounted keeps the button, greyed out, with the reason on it.
function rowAction(volume, { busy, platform, handlers }) {
  if (busy) return h("span", { class: "devices-busy" }, h("i", { class: "ring" }));
  if (isMounted(volume)) return volume.actions.includes("unmount") && button({ label: "Unmount", small: true, title: "Take it out of use without unplugging the disk", onclick: () => handlers.unmount(volume) });
  if (volume.helper) return null;
  if (volume.actions.includes("mount")) return button({ label: "Mount", glyph: "plug", tone: "primary", small: true, title: "Make its files reachable", onclick: () => handlers.mount(volume) });
  if (handsOver(volume)) return button({ label: "Mount…", glyph: "plug", tone: "primary", small: true, title: "Choose where and how to mount it", onclick: () => handlers.handOver(volume) });
  const blocked = button({ label: "Mount", glyph: "plug", small: true, title: whyNoMount(volume, platform) });
  blocked.disabled = true;
  return blocked;
}

function detail({ volume, group }, { platform, handlers }) {
  const [formatName, formatNote] = formatOf(volume);
  const [, roleNote] = roleOf(volume);
  const blocked = !isMounted(volume) && !volume.helper && !volume.actions.includes("mount") && !handsOver(volume);
  return h(
    "div",
    { class: "devices-detail" },
    keyValue([
      ["What it is", [roleNote, volume.home && "Your home folder is on it."].filter(Boolean).join(" ")],
      ["Format", [formatName, formatNote].filter(Boolean).join(". ")],
      ["Mounted at", isMounted(volume) ? pathChip(volume.mount_point) : "Nowhere yet. It is connected, but its files cannot be reached until it is mounted."],
      [group.disk ? "Device" : "Shared from", copyChip(volume.device)],
      ["Space", volume.answering ? spaceSentence(volume, sharingOf(volume, group)) : "The computer that shares it is not answering, so how full it is does not show."],
      ["Protection", volume.encrypted && (volume.locked ? "Encrypted and locked." : "Encrypted. Nothing on it can be read without its password.")],
      ["Writing", isMounted(volume) && volume.read_only && "Read-only. Nothing on it can be changed from this computer."],
      ["Mounting", blocked && whyNoMount(volume, platform)],
      ["On", group.disk && `${group.title}, ${size(group.disk.size)}`],
    ]),
    h(
      "div",
      { class: "devices-more" },
      !isMounted(volume) && volume.actions.includes("mount") && handsOver(volume) && button({ label: "Mount somewhere else", glyph: "folder", small: true, title: "Choose the folder it is mounted in", onclick: () => handlers.handOver(volume) }),
      volume.home && button({ label: "Free up space", glyph: "trash", small: true, onclick: () => (location.hash = CLEANUP_HASH) }),
    ),
  );
}

// One volume: what it is called, where it is mounted, how full it is, and the one thing to do with it. `slot` is the hue its stretch of the
// disk bar wears; a row with no bar over it (a share, or any row of a ranked list) leads with a small picture of where it lives instead.
export function volumeRow(row, { slot, view, platform, handlers, ranked }) {
  const { volume, group } = row;
  const pressure = pressureOf(volume);
  const open = view.open.has(volume.id);
  const kind = [formatOf(volume)[0], roleOf(volume)[0], ranked && group.disk && `on ${group.title}`].filter(Boolean).join(" · ");
  const more = iconButton("down", open ? "Show less" : "More about it", () => handlers.toggle(volume));
  more.classList.add("devices-toggle");
  more.setAttribute("aria-expanded", String(open));
  const main = h(
    "div",
    { class: "devices-main" },
    slot ? h("i", { class: "devices-dot", "data-slot": slot }) : h("span", { class: "devices-glyph" }, icon(PLACES[group.place].glyph, 15)),
    h(
      "div",
      { class: "devices-name" },
      h("strong", { text: volumeName(volume) }),
      h(
        "span",
        { class: "devices-kind" },
        h("span", { text: kind }),
        volume.home && flag("home", "Home folder", "accent", "Your home folder is on this volume"),
        volume.encrypted && flag("lock", volume.locked ? "Locked" : "Encrypted", volume.locked ? "warn" : "", volume.locked ? "Encrypted, and not unlocked yet" : "Nothing on it can be read without its password"),
        isMounted(volume) && volume.read_only && flag("eye", "Read-only", "", "Nothing on it can be changed from this computer"),
        pressure && flag("alert", PRESSURE[pressure], pressure, `${size(volume.free)} is left`),
        !volume.answering && flag("alert", "Not answering", "warn", "The computer that shares it does not respond"),
      ),
    ),
    h("div", { class: "devices-where" }, isMounted(volume) ? pathChip(volume.mount_point) : pill("Not mounted")),
    usage(volume, pressure),
    h("div", { class: "devices-actions" }, rowAction(volume, { busy: view.busy.has(volume.id), platform, handlers }), more),
  );
  main.addEventListener("click", (event) => !event.target.closest("button, a") && handlers.toggle(volume));
  return h("li", { class: `devices-row${open ? " open" : ""}${volume.helper ? " helper" : ""}`, "data-key": volume.helper ? "parts" : volume.id }, main, open && detail(row, { platform, handlers }));
}
