import { h } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { query } from "../data.js";
import { createLivePanel } from "../live_panel.js";
import { rise } from "../motion.js";
import { createView, editButton, linkCard, toolButton, toolGrid } from "../space_kit.js";
import { glyphTile, notice, sectionHead, stat } from "../widgets.js";
import { friendlyText, plural, titleOf } from "../words.js";
import { appliesHere, backupGroup } from "./data_backups.js";

const PROTECT_TOOLS = ["devops data encrypt", "devops data decrypt", "devops data subset", "devops data validate"];
const CLOUD_TOOLS = ["cloud sync", "cloud copy", "cloud mount", "cloud transfer"];

export function createDataSpace({ activity, tools }) {
  const panel = createLivePanel({
    title: "What is backed up", path: "devops data list", extra: ["--json"],
    actions: [editButton(activity, { title: "the backup list", kind: "data" }, { label: "Edit the list", small: true })],
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
      const counted = `${plural(entries.length, "item")} · ${plural(groups.size, "group")}`;
      setCount(counted);
      const tiles = [
        [stat({ glyph: "database", hue: 252, label: "Backed up" }), entries.length, `in ${plural(groups.size, "group")}`],
        [stat({ glyph: "cpu", hue: 200, label: "For this machine" }), here, here === entries.length ? "all of them apply here" : `${entries.length - here} are for other systems`],
        [stat({ glyph: "lock", hue: 155, label: "Encrypted" }), encrypted, encrypted === entries.length ? "everything is protected" : `${entries.length - encrypted} kept as they are`],
        [stat({ glyph: "share", hue: 30, label: "Share links" }), linked, linked ? "retrievable without signing in" : "none set up yet"],
      ];
      requestAnimationFrame(() => tiles.forEach(([tile, value, note]) => tile.set(value, note)));
      const sections = [...groups].map(([name, items]) => [name, backupGroup({ activity, tools, name, items, source: data.source })]);
      const stack = h("div", { class: "stack" }, rise(h("div", { class: "stats" }, tiles.map(([tile]) => tile.element))), sections.map(([, section]) => section.element));
      // One more read on every load says where backups go and which groups are the user's own, asked afresh so that Refresh covers it too.
      // It reads only the user's file, and a user group replaces a built-in group of the same name whole, so a group is either the user's or built in.
      query(["devops", "self", "status", "--backup", "--json"], true).then(
        (result) => {
          if (!stack.isConnected) return;
          const { details } = result.json.backup;
          for (const [name, section] of sections) section.setOrigin(data.source !== "library" && Object.hasOwn(details.backup_items, name));
          setCount(`${counted} · ${details.cloud_config ? `kept in ${details.cloud_config}` : "no cloud chosen"}`);
          if (details.cloud_selection_required) {
            stack.prepend(
              h(
                "div",
                { class: "session-row" },
                glyphTile("alert", 30, 40),
                h("div", { class: "session-text" }, h("strong", { text: "No cloud is chosen for your backups" }), h("span", { class: "dim", text: "Until one is, backing up or retrieving asks which cloud to use every time." })),
                toolButton(tools, "devops config setup cloud", { label: "Choose a cloud", tone: "primary" }),
              ),
            );
          }
        },
        (error) => stack.isConnected && stack.prepend(h("p", { class: "dim", text: `Could not tell which groups are yours, or where your backups are kept: ${error.message}` })),
      );
      return stack;
    },
  });

  const cloudGrid = toolGrid(tools, CLOUD_TOOLS);
  const onedrive = state.nodes.get("cloud onedrive");
  if (onedrive) cloudGrid.append(linkCard({ href: "#/tools/cloud/onedrive", emoji: onedrive.icon || "🗂️", name: onedrive.path, title: titleOf(onedrive), blurb: friendlyText(onedrive.summary) }));

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
    h("section", { class: "block" }, sectionHead("Cloud storage"), cloudGrid),
  );
  return { element, show: () => panel.ensure() };
}
