import { h } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { createLivePanel } from "../live_panel.js";
import { rise } from "../motion.js";
import { dataTable } from "../result_view.js";
import { createView, toolButton, toolCard } from "../space_kit.js";
import { notice, segmented, stat } from "../widgets.js";
import { formatBytes, plural } from "../words.js";

const IN_SYNC = "Configured";

export function createDotfilesSpace({ tools }) {
  let scope = "user";

  const panel = createLivePanel({
    title: "What is managed", path: "devops config dotfiles status", extra: ["--json"],
    render: (data, { setCount }) => {
      if (!data?.sync) return notice({ glyph: "sync", title: "Nothing is managed yet", body: "Collect the settings files on this machine to start keeping them in sync.", action: toolButton(tools, "devops config dotfiles collect", { label: "Collect my settings", tone: "primary" }) });
      const everything = [...data.sync.user, ...data.sync.library];
      const synced = everything.filter((entry) => entry.status === IN_SYNC).length;
      const collectable = (data.radar ?? []).filter((entry) => entry.verdict === "collect").length;
      setCount(`${plural(everything.length, "file")} · ${synced} in sync`);
      const tiles = [
        [stat({ glyph: "check", hue: 155, label: "In sync" }), synced, `of ${everything.length} managed files`],
        [stat({ glyph: "alert", hue: 30, label: "Need attention" }), everything.length - synced, "differ or are missing"],
        [stat({ glyph: "plus", hue: 252, label: "Ready to collect" }), collectable, "found here, not yet managed"],
        [stat({ glyph: "folder", hue: 200, label: "Stored" }), formatBytes(data.storage?.dotfiles_root_footprint?.size_bytes ?? 0), `${(data.storage?.dotfiles_root_footprint?.files ?? 0).toLocaleString()} files kept safe`],
      ];
      const holder = h("div", { class: "table-holder" });
      const paint = () => {
        const rows = data.sync[scope].map((entry) => ({ program: entry.program, file: entry.file_name, status: entry.status, method: entry.method, location: entry.default_path, stored_at: entry.managed_path }));
        holder.replaceChildren(rows.length ? dataTable(rows) : notice({ glyph: "folder", title: "Nothing here", body: "No files of this kind are managed." }));
      };
      const picker = segmented([["user", `Yours · ${data.sync.user.length}`], ["library", `Built in · ${data.sync.library.length}`]], (value) => {
        scope = value;
        picker.set(scope);
        paint();
      });
      picker.set(scope);
      paint();
      requestAnimationFrame(() => tiles.forEach(([tile, value, note]) => tile.set(value, note)));
      return h("div", { class: "stack" }, rise(h("div", { class: "stats" }, tiles.map(([tile]) => tile.element))), h("div", { class: "table-bar" }, picker.element), holder);
    },
  });

  const element = createView(
    {
      title: "Dotfiles", lede: "Your settings files, kept in one safe place and applied wherever you work.",
      actions: [
        toolButton(tools, "devops config dotfiles collect", { label: "Collect", glyph: "plus" }),
        toolButton(tools, "devops config dotfiles sync", { label: "Save from this machine", glyph: "up", preset: { direction: "up" } }),
        toolButton(tools, "devops config dotfiles sync", { label: "Apply to this machine", glyph: "download", tone: "primary", preset: { direction: "down" } }),
      ],
    },
    panel.element,
    h(
      "div",
      { class: "tool-grid" },
      [["devops config dotfiles export", "Move to a new machine"], ["devops config dotfiles import", "Bring settings from another machine"], ["devops config dotfiles register", "Add one file"]]
        .filter(([path]) => state.nodes.has(path))
        .map(([path, label]) => toolCard(tools, state.nodes.get(path), label)),
    ),
  );

  return { element, show: () => panel.ensure() };
}
