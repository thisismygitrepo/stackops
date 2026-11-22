import { h, icon, toast } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { rise } from "../motion.js";
import { confirmAction } from "../overlays.js";
import { avatar, button, copyChip, pill } from "../widgets.js";

const SYSTEM_NAMES = { linux: "Linux", darwin: "macOS", windows: "Windows" };
const AUTOMATIC_CLOUD_PATH = "^";
// `register` rewrites every other character in a group or entry name, so saving such an entry from the form would add a second one beside it.
const KEPT_NAME = /^[A-Za-z0-9_]+$/;

export const appliesHere = (item) => item.entry.os.some((system) => SYSTEM_NAMES[system] === state.boot.platform);

// One group of the backup list. `setOrigin` is called once it is known whether the group comes from the user's own file; only those entries can be changed.
export function backupGroup({ activity, tools, name, items, source }) {
  const editable = [];
  const sync = (title, emoji, direction, which, extra) =>
    activity.start({ title, emoji, arguments: ["devops", "data", "sync", direction, "--which", which, "--source", source, ...extra], interactive: true, reveal: true }).catch((error) => toast(error.message));

  async function retrieve(item, byLink) {
    const from = byLink ? "behind its share link" : "in the cloud";
    const sure = await confirmAction({ title: `Retrieve “${item.name}”?`, body: `The copy ${from} is brought back to ${item.entry.path_local} on this machine. What is already there may be replaced.`, confirm: "Retrieve" });
    if (sure) sync(`Retrieve ${item.name}`, "📥", "down", item.selector, byLink ? ["--use-link"] : []);
  }

  // `register` replaces the entry with the same group and name and writes only what it is given, so every value the entry has goes into the form.
  // Not strictly complete: a note cannot be emptied here, because the form has no way to send an empty value. The whole list can be edited for that.
  function edit(item) {
    const { entry } = item;
    const preset = { path_local: entry.path_local, group: name, name: item.name, os: entry.os.join(",") };
    if (entry.path_cloud && entry.path_cloud !== AUTOMATIC_CLOUD_PATH) preset.path_cloud = entry.path_cloud;
    if (entry.share_url) preset.share_url = entry.share_url;
    if (entry.encryption) preset.encryption = entry.encryption;
    if (entry.note) preset.note = entry.note;
    if (!entry.zip) preset.no_zip = "on";
    if (!entry.rel2home) preset.absolute_path = "on";
    tools.open("devops data register", { preset, title: "Edit this backup" });
  }

  function row(item) {
    const { entry } = item;
    const applies = appliesHere(item);
    // The list says whether the path is on this machine. One that is not has nothing to send, so its Back up is switched off and the row says why.
    const missing = applies && !item.local_exists;
    const cloud = entry.path_cloud === null || entry.path_cloud === AUTOMATIC_CLOUD_PATH ? "Automatic" : entry.path_cloud;
    const backUp = button({
      label: "Back up", glyph: "up", small: true, tone: "primary", title: missing ? "Nothing to back up. This path does not exist on this machine." : undefined,
      onclick: () => sync(`Back up ${item.name}`, "📤", "up", item.selector, []),
    });
    backUp.disabled = missing;
    const actions = h(
      "div",
      { class: "backup-actions" },
      entry.share_url && button({ label: "By link", glyph: "share", small: true, title: "Retrieve it from its share link, without signing in to cloud storage", onclick: () => retrieve(item, true) }),
      button({ label: "Retrieve", glyph: "download", small: true, onclick: () => retrieve(item, false) }),
      backUp,
    );
    // `register` refuses a path that is not on this machine, so entries for other systems get no Edit.
    if (applies && KEPT_NAME.test(name) && KEPT_NAME.test(item.name)) editable.push([actions, item]);
    return h(
      "li",
      { class: `session-row backup-row${applies ? "" : " muted"}` },
      avatar(item.name, 40),
      h("div", { class: "session-text" }, h("strong", { text: item.name }), copyChip(entry.path_local), entry.note && h("span", { class: "dim", text: entry.note })),
      h(
        "div",
        { class: "backup-facts" },
        missing && pill("Missing on this machine", "warn"),
        h("span", { class: "fact", title: "Where it is kept in the cloud" }, icon("sync", 13), cloud),
        entry.encryption ? pill(entry.encryption === "symmetric" ? "Encrypted · password" : "Encrypted · key", "good") : pill("Not encrypted", "warn"),
        entry.zip && pill("Zipped"),
        entry.share_url && copyChip(entry.share_url, "Share link"),
        entry.os.length < Object.keys(SYSTEM_NAMES).length && pill(entry.os.map((system) => SYSTEM_NAMES[system]).join(" · ")),
      ),
      applies && actions,
    );
  }

  const title = h("h3", {}, name, h("b", { text: String(items.length) }));
  // A design choice: the group button only shows where it saves clicks, on a group with several entries that are on this machine.
  // It names the group, unless some of its entries are missing here: one missing path stops the whole run, so then it names the ones that can be sent.
  const here = items.filter(appliesHere);
  const present = here.filter((item) => item.local_exists);
  const element = h(
    "section",
    { class: "backup-group" },
    h(
      "header",
      { class: "backup-head" },
      title,
      h("span", { class: "spacer" }),
      present.length > 1 &&
        button({
          label: "Back up group", glyph: "up", small: true, title: "Back up every entry in this group that exists on this machine",
          onclick: () => sync(`Back up ${name}`, "📤", "up", present.length === here.length ? name : present.map((item) => item.selector).join(","), []),
        }),
    ),
    rise(h("ul", { class: "session-list" }, items.map(row))),
  );

  function setOrigin(mine) {
    title.after(pill(mine ? "Yours" : "Built in", mine ? "accent" : ""));
    if (!mine) return;
    for (const [actions, item] of editable) actions.prepend(button({ label: "Edit", glyph: "sliders", small: true, title: "Change where it is kept, its protection, or its note", onclick: () => edit(item) }));
  }

  return { element, setOrigin };
}
