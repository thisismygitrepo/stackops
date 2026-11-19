import { h, icon, toast } from "/assets/scripts/dom.js";
import { createLivePanel } from "../live_panel.js";
import { rise } from "../motion.js";
import { confirmAction } from "../overlays.js";
import { createView, toolButton } from "../space_kit.js";
import { avatar, button, notice, pill } from "../widgets.js";
import { plural, relativeTime } from "../words.js";

const PREVIEW_CELLS = 12;

export function createSessionsSpace({ activity, tools }) {
  const launch = (layout) =>
    activity.start({ title: `Launch ${layout.name}`, emoji: "🏃", arguments: ["terminal", "run", "--choose-layouts", layout.name], interactive: true, reveal: true }).catch((error) => toast(error.message));

  async function end(session) {
    const sure = await confirmAction({ title: `End “${session.name}”?`, body: "Everything running inside this session stops. This cannot be undone.", confirm: "End session", tone: "danger" });
    if (sure) activity.start({ title: `End ${session.name}`, emoji: "💀", arguments: ["terminal", "kill", session.name], interactive: true, reveal: true }).catch((error) => toast(error.message));
  }

  const layouts = createLivePanel({
    title: "Saved layouts", path: "terminal list", extra: ["--json"], skeletonShape: "card",
    render: (data, { setCount }) => {
      const items = data?.layouts ?? [];
      setCount(items.length ? plural(items.length, "layout") : "");
      if (items.length === 0) return notice({ glyph: "layers", title: "No saved layouts", body: "A layout is a set of tabs and panes you can start in one click.", action: toolButton(tools, "terminal create-template", { label: "Create one", tone: "primary" }) });
      return rise(
        h(
          "div",
          { class: "card-grid" },
          items.map((layout) =>
            h(
              "article",
              { class: "layout-card lit" },
              h("div", { class: "layout-preview", "aria-hidden": "true" }, Array.from({ length: Math.min(layout.pane_count, PREVIEW_CELLS) }, (_, index) => h("i", { style: `--i:${index}` }))),
              h("h3", { text: layout.name }),
              h("p", { class: "dim", text: `${plural(layout.tab_count, "tab")} · ${plural(layout.pane_count, "pane")}` }),
              h("footer", {}, pill(layout.selector.split(":")[0], ""), button({ label: "Launch", glyph: "play", small: true, tone: "primary", onclick: () => launch(layout) })),
            ),
          ),
        ),
      );
    },
  });

  const running = createLivePanel({
    title: "Running now", path: "terminal summary", extra: ["--json"],
    render: (data, { setCount }) => {
      const sessions = data?.sessions ?? [];
      setCount(sessions.length ? `${plural(sessions.length, "session")} · ${data.backend}` : "");
      if (sessions.length === 0) return notice({ glyph: "layers", title: "Nothing is running", body: "Launch a layout above to start a session." });
      return rise(
        h(
          "ul",
          { class: "session-list" },
          sessions.map((session) => {
            const total = Math.max(session.running + session.idle + session.unknown, 1);
            return h(
              "li",
              { class: "session-row" },
              avatar(session.name, 40),
              h("div", { class: "session-text" }, h("strong", { text: session.name }), h("span", { class: "dim", text: `${plural(session.window_count, "window")} · active ${relativeTime(session.last_active)}` })),
              h("div", { class: "meter", title: `${session.running} busy, ${session.idle} idle` }, h("i", { class: "busy", style: `--share:${session.running / total}` }), h("i", { class: "idle", style: `--share:${session.idle / total}` })),
              h("span", { class: "session-counts dim" }, `${session.running} busy · ${session.idle} idle`),
              session.attached ? pill("In use", "good") : pill("In background", ""),
              h("button", { class: "icon-btn danger", type: "button", title: "End this session", "aria-label": `End ${session.name}`, onclick: () => end(session) }, icon("stop", 15)),
            );
          }),
        ),
      );
    },
  });

  const element = createView(
    {
      title: "Sessions", lede: "Start a saved workspace, or see what is already running.",
      actions: [toolButton(tools, "terminal export", { label: "Save current as layout", glyph: "plus" }), toolButton(tools, "terminal run", { label: "Launch with options", glyph: "sliders" })],
    },
    layouts.element,
    running.element,
  );
  return {
    element,
    show() {
      layouts.ensure();
      running.ensure();
    },
  };
}
