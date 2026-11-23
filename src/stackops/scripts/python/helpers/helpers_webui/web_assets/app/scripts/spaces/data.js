import { h } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { query } from "../data.js";
import { createLivePanel } from "../live_panel.js";
import { rise } from "../motion.js";
import { createView, editButton, linkCard, toolButton, toolGrid } from "../space_kit.js";
import { glyphTile, notice, sectionHead, segmented, stat } from "../widgets.js";
import { friendlyText, plural, titleOf } from "../words.js";
import { appliesHere, backupGroup } from "./data_backups.js";

const PROTECT_TOOLS = ["devops data encrypt", "devops data decrypt", "devops data subset", "devops data validate"];
const CLOUD_TOOLS = ["cloud sync", "cloud copy", "cloud mount", "cloud transfer"];

export function createDataSpace({ activity, tools }) {
  // Kept outside the panel's render so it survives a refresh: the panel reloads when a backup ends.
  let everySystem = false;

  const panel = createLivePanel({
    title: "What is backed up", path: "devops data list", extra: ["--json"], surface: { source: "Which backup list to read" },
    actions: [editButton(activity, { title: "the backup list", kind: "data" }, { label: "Edit the list", small: true })],
    render: (data, { setCount }) => {
      const entries = data?.entries ?? [];
      if (entries.length === 0) {
        setCount("");
        return notice({ glyph: "database", title: "Nothing is backed up yet", body: "Add a file or folder and StackOps keeps a copy of it in your cloud storage.", action: toolButton(tools, "devops data register", { label: "Add a backup", tone: "primary" }) });
      }
      const sorted = [...entries].sort((left, right) => appliesHere(right) - appliesHere(left));
      const local = sorted.filter(appliesHere);
      const others = entries.length - local.length;
      const total = stat({ glyph: "database", hue: 252, label: "Backed up" });
      const here = stat({ glyph: "cpu", hue: 200, label: "For this machine" });
      const encrypted = stat({ glyph: "lock", hue: 155, label: "Encrypted" });
      const linked = stat({ glyph: "share", hue: 30, label: "Share links" });
      const holder = h("div", { class: "stack" });
      let sections = [];
      let counted = "";
      // Both are filled in by the second read below.
      let origin = null;
      let kept = "";

      // Entries for other systems stay out of the way unless they are asked for, and the numbers describe what is listed.
      const paint = () => {
        const shown = everySystem ? sorted : local;
        const groups = Map.groupBy(shown, (item) => item.group);
        const safe = shown.filter((item) => item.entry.encryption).length;
        const links = shown.filter((item) => item.entry.share_url).length;
        counted = `${plural(shown.length, "item")} · ${plural(groups.size, "group")}`;
        setCount(`${counted}${kept}`);
        requestAnimationFrame(() => {
          total.set(shown.length, `in ${plural(groups.size, "group")}`);
          here.set(local.length, others === 0 ? "all of them apply here" : everySystem ? `${others} are for other systems` : `${others} for other systems are hidden`);
          encrypted.set(safe, safe < shown.length ? `${shown.length - safe} kept as they are` : safe ? "everything is protected" : "nothing listed");
          linked.set(links, links ? "retrievable without signing in" : "none set up yet");
        });
        sections = [...groups].map(([name, items]) => [name, backupGroup({ activity, tools, name, items, source: data.source })]);
        if (origin) for (const [name, section] of sections) section.setOrigin(origin(name));
        if (sections.length) holder.replaceChildren(...sections.map(([, section]) => section.element));
        else holder.replaceChildren(notice({ glyph: "database", title: "Nothing here is for this machine", body: "Everything on the list is for other systems. Choose All systems to see it." }));
      };
      const picker = segmented([[false, `This machine · ${local.length}`], [true, `All systems · ${entries.length}`]], (value) => {
        everySystem = value;
        picker.set(everySystem);
        paint();
      });
      picker.set(everySystem);
      paint();
      const stack = h("div", { class: "stack" }, rise(h("div", { class: "stats" }, [total, here, encrypted, linked].map((tile) => tile.element))), others > 0 && h("div", { class: "table-bar" }, picker.element), holder);
      // One more read on every load says where backups go and which groups are the user's own, asked afresh so that Refresh covers it too.
      // It reads only the user's file, and a user group replaces a built-in group of the same name whole, so a group is either the user's or built in.
      query(["devops", "self", "status", "--backup", "--json"], true).then(
        (result) => {
          if (!stack.isConnected) return;
          const { details } = result.json.backup;
          origin = (name) => data.source !== "library" && Object.hasOwn(details.backup_items, name);
          kept = ` · ${details.cloud_config ? `kept in ${details.cloud_config}` : "no cloud chosen"}`;
          for (const [name, section] of sections) section.setOrigin(origin(name));
          setCount(`${counted}${kept}`);
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
