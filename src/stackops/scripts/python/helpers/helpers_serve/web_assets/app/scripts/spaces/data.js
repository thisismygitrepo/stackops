import { h, icon, toast } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { createLivePanel } from "../live_panel.js";
import { rise } from "../motion.js";
import { confirmAction } from "../overlays.js";
import { createView, toolButton, toolGrid } from "../space_kit.js";
import { avatar, button, copyChip, notice, pill, sectionHead, stat } from "../widgets.js";
import { plural } from "../words.js";

const PROTECT_TOOLS = ["devops data encrypt", "devops data decrypt", "devops data subset", "devops data validate"];
const CLOUD_TOOLS = ["cloud sync", "cloud copy", "cloud mount", "cloud transfer"];
const SYSTEM_NAMES = { linux: "Linux", darwin: "macOS", windows: "Windows" };
const AUTOMATIC_CLOUD_PATH = "^";

export function createDataSpace({ activity, tools }) {
  const thisSystem = Object.keys(SYSTEM_NAMES).find((system) => SYSTEM_NAMES[system] === state.boot.platform);
  const appliesHere = (item) => item.entry.os.includes(thisSystem);
  const sync = (title, emoji, direction, item, source) =>
    activity.start({ title, emoji, arguments: ["devops", "data", "sync", direction, "--which", item.selector, "--source", source], interactive: true, reveal: true }).catch((error) => toast(error.message));

  async function retrieve(item, source) {
    const sure = await confirmAction({ title: `Retrieve “${item.name}”?`, body: `The copy in the cloud is brought back to ${item.entry.path_local} on this machine. What is already there may be replaced.`, confirm: "Retrieve" });
    if (sure) sync(`Retrieve ${item.name}`, "📥", "down", item, source);
  }

  function row(item, source) {
    const { entry } = item;
    const applies = appliesHere(item);
    const cloud = entry.path_cloud === null || entry.path_cloud === AUTOMATIC_CLOUD_PATH ? "Automatic" : entry.path_cloud;
    return h(
      "li",
      { class: `session-row backup-row${applies ? "" : " muted"}` },
      avatar(item.name, 40),
      h("div", { class: "session-text" }, h("strong", { text: item.name }), copyChip(entry.path_local), entry.note && h("span", { class: "dim", text: entry.note })),
      h(
        "div",
        { class: "backup-facts" },
        h("span", { class: "fact", title: "Where it is kept in the cloud" }, icon("sync", 13), cloud),
        entry.encryption ? pill(entry.encryption === "symmetric" ? "Encrypted · password" : "Encrypted · key", "good") : pill("Not encrypted", "warn"),
        entry.zip && pill("Zipped"),
        entry.share_url && pill("Share link", "accent"),
        entry.os.length < Object.keys(SYSTEM_NAMES).length && pill(entry.os.map((system) => SYSTEM_NAMES[system]).join(" · ")),
      ),
      applies && button({ label: "Retrieve", glyph: "download", small: true, onclick: () => retrieve(item, source) }),
      applies && button({ label: "Back up", glyph: "up", small: true, tone: "primary", onclick: () => sync(`Back up ${item.name}`, "📤", "up", item, source) }),
    );
  }

  const panel = createLivePanel({
    title: "What is backed up", path: "devops data list", extra: ["--json"],
    render: (data, { setCount }) => {
      const entries = data?.entries ?? [];
      if (entries.length === 0) {
        setCount("");
        return notice({ glyph: "database", title: "Nothing is backed up yet", body: "Add a file or folder and StackOps keeps a copy of it in your cloud storage.", action: toolButton(tools, "devops data register", { label: "Add a backup", tone: "primary" }) });
      }
      const groups = Map.groupBy([...entries].sort((left, right) => appliesHere(right) - appliesHere(left)), (item) => item.group);
      const here = entries.filter(appliesHere).length;
      const encrypted = entries.filter((item) => item.entry.encryption).length;
      const linked = entries.filter((item) => item.entry.share_url).length;
      setCount(`${plural(entries.length, "item")} · ${plural(groups.size, "group")}`);
      const tiles = [
        [stat({ glyph: "database", hue: 252, label: "Backed up" }), entries.length, `in ${plural(groups.size, "group")}`],
        [stat({ glyph: "cpu", hue: 200, label: "For this machine" }), here, here === entries.length ? "all of them apply here" : `${entries.length - here} are for other systems`],
        [stat({ glyph: "lock", hue: 155, label: "Encrypted" }), encrypted, encrypted === entries.length ? "everything is protected" : `${entries.length - encrypted} kept as they are`],
        [stat({ glyph: "share", hue: 30, label: "Share links" }), linked, linked ? "retrievable without signing in" : "none set up yet"],
      ];
      requestAnimationFrame(() => tiles.forEach(([tile, value, note]) => tile.set(value, note)));
      return h(
        "div",
        { class: "stack" },
        rise(h("div", { class: "stats" }, tiles.map(([tile]) => tile.element))),
        [...groups].map(([name, items]) => h("section", { class: "backup-group" }, h("h3", {}, name, h("b", { text: String(items.length) })), rise(h("ul", { class: "session-list" }, items.map((item) => row(item, data.source)))))),
      );
    },
  });

  const element = createView(
    {
      title: "Data", lede: "The files and folders StackOps keeps safe in your cloud storage, and ways to move them around.",
      actions: [
        toolButton(tools, "devops data register", { label: "Add a backup", glyph: "plus" }),
        toolButton(tools, "devops data sync", { label: "Retrieve everything", glyph: "download", preset: { direction: "down", which: "all" } }),
        toolButton(tools, "devops data sync", { label: "Back up everything", glyph: "up", tone: "primary", preset: { direction: "up", which: "all" } }),
      ],
    },
    panel.element,
    h("section", { class: "block" }, sectionHead("Protect and tidy"), toolGrid(tools, PROTECT_TOOLS)),
    h("section", { class: "block" }, sectionHead("Cloud storage"), toolGrid(tools, CLOUD_TOOLS)),
  );
  return { element, show: () => panel.ensure() };
}
