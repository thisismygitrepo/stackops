import { statusGlyph } from "./dock.js";
import { formatClock, formatDuration, h, icon, toast } from "./dom.js";
import { DASHBOARDS, QUICK_ACTIONS } from "./presets.js";
import { nodeHash, on, state } from "./state.js";

export function createHomeView({ dock }) {
  const { boot } = state;
  const recent = h("div");

  const section = (title, content, count) =>
    h(
      "section",
      { class: "section" },
      h("div", { class: "section-head" }, h("h2", { text: title }), count !== undefined && h("span", { class: "count", text: String(count) })),
      content,
    );

  const dashboardCards = DASHBOARDS.map((board) =>
    h(
      "a",
      { class: "card", href: `#/d/${board.id}` },
      h("span", { class: "emoji", text: board.icon }),
      h("span", { class: "title" }, h("span", { class: "name", text: board.title })),
      h("span", { class: "blurb", text: board.blurb }),
    ),
  );

  const actionCards = QUICK_ACTIONS.filter((action) => state.nodes.has(action.path)).map((action) => {
    const node = state.nodes.get(action.path);
    const body = [
      h("span", { class: "emoji", text: node.icon || "▫️" }),
      h(
        "span",
        { class: "title" },
        h("span", { class: "name", text: action.label }),
        h("span", { class: "tail" }, action.run ? [icon("play", 11), "Run"] : ["Options", icon("arrow", 12)]),
      ),
      h("span", { class: "blurb", text: node.summary }),
    ];
    if (!action.run) return h("a", { class: "card action", href: nodeHash(node), title: `stackops ${action.path}` }, body);
    const button = h("button", { class: "card action", title: `Runs: stackops ${action.path}` }, body);
    button.addEventListener("click", async () => {
      button.classList.add("busy");
      try {
        await dock.start({ arguments: action.path.split(" "), interactive: true, reveal: true });
      } catch (error) {
        toast(error.message);
      }
      button.classList.remove("busy");
    });
    return button;
  });

  const groupCards = boot.tree.children.map((node) =>
    h(
      "a",
      { class: "card", href: nodeHash(node) },
      h("span", { class: "emoji", text: node.icon || "▫️" }),
      h(
        "span",
        { class: "title" },
        h("span", { class: "name", text: node.name }),
        h("span", { class: "tail", text: node.kind === "command" ? "command" : `${node.leaves} commands` }),
      ),
      h("span", { class: "blurb", text: node.summary }),
    ),
  );

  function showRecent() {
    const runs = dock.runs().sort((left, right) => right.started_at - left.started_at).slice(0, 8);
    if (runs.length === 0) {
      recent.replaceChildren(h("p", { class: "empty", text: "Nothing has run in this session yet. Pick a quick action, or open any command and press Run." }));
      return;
    }
    recent.replaceChildren(
      h(
        "ul",
        { class: "runs-list" },
        runs.map((run) =>
          h(
            "li",
            {},
            h(
              "button",
              { title: "Show this run in the terminal dock", onclick: () => dock.focus(run.id) },
              statusGlyph(run),
              h("code", { text: run.command_line }),
              h("span", {
                class: "when",
                text: `${formatClock(run.started_at)} · ${run.finished_at === null ? "running" : formatDuration(run.finished_at - run.started_at)}`,
              }),
            ),
          ),
        ),
      ),
    );
  }

  const element = h(
    "section",
    { class: "view" },
    h(
      "header",
      { class: "hero" },
      h("h1", { text: "StackOps" }),
      h("p", { text: "Run any StackOps command from here: fill in a form, press a button, and watch it in a real terminal." }),
      h(
        "div",
        { class: "facts" },
        h("span", { class: "chip", text: `${boot.user}@${boot.host}` }),
        h("span", { class: "chip", text: boot.platform }),
        h("span", { class: "chip", text: `v${boot.version}` }),
        h("span", { class: "chip", text: `${boot.tree.leaves} commands` }),
      ),
    ),
    section("Dashboards", h("div", { class: "cards" }, dashboardCards)),
    section("Quick actions", h("div", { class: "cards" }, actionCards)),
    section("Command groups", h("div", { class: "cards" }, groupCards)),
    section("Recent runs", recent),
  );

  on("runs", showRecent);
  showRecent();
  return { element, show: () => [{ label: "Home" }] };
}
