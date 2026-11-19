import { formatClock, formatDuration, h, icon } from "/assets/scripts/dom.js";
import { on, state } from "/assets/scripts/state.js";
import { QUICK_TASKS } from "../catalog.js";
import { query, software } from "../data.js";
import { createHeroOrbit } from "../hero_orbit.js";
import { rise } from "../motion.js";
import { glyphTile, notice, pill, sectionHead, stat } from "../widgets.js";
import { greeting } from "../words.js";

// The parts of the CLI's health check the four counts do not already cover, and the page that deals with each.
// A design choice: managed settings are left out, since that part alone takes several seconds and Dotfiles shows it.
const HEALTH = [["shell", "Shell profile", "#/reports/status"], ["ssh", "SSH", "#/network"], ["backup", "Backups", "#/data"]];
const HEALTH_TONES = { ready: "good", attention: "warn", error: "bad" };

export function createHomeSpace({ activity, tools, openSearch }) {
  const { boot } = state;
  const name = boot.user.charAt(0).toUpperCase() + boot.user.slice(1);
  const recent = h("div", { class: "recent" });
  const stats = {
    apps: stat({ glyph: "apps", hue: 252, label: "Apps installed", href: "#/apps" }),
    projects: stat({ glyph: "branch", hue: 150, label: "Projects", href: "#/projects" }),
    sessions: stat({ glyph: "layers", hue: 290, label: "Sessions", href: "#/sessions" }),
    agents: stat({ glyph: "bot", hue: 20, label: "Agents", href: "#/agents" }),
  };
  const health = HEALTH.map(([key, label, href]) => {
    const mark = pill("Checking…");
    return { key, mark, element: h("a", { href }, h("span", { text: label }), mark) };
  });
  let stale = true;

  const tasks =QUICK_TASKS.filter((task) => !task.tool || state.nodes.has(task.tool)).map((task) =>
    h(
      "button",
      { class: "task-card lit", type: "button", style: `--hue:${task.tint}`, onclick: () => (task.tool ? tools.open(task.tool, { preset: task.preset ?? {} }) : (location.hash = task.hash)) },
      glyphTile(task.glyph, task.tint, 42),
      h("strong", { text: task.title }),
      h("span", { text: task.blurb }),
      h("i", { class: "task-go" }, icon("arrow", 14)),
    ),
  );

  const element = h(
    "section",
    { class: "view home", hidden: true },
    h(
      "header",
      { class: "hero" },
      createHeroOrbit(),
      h("span", { class: "overline", text: `${boot.host} · ${boot.platform}` }),
      h("h1", {}, `${greeting()}, `, h("em", { text: name })),
      h("p", { text: "Your machine, apps, projects, and agents — one click away." }),
      h(
        "button",
        { class: "hero-search", type: "button", onclick: () => openSearch() },
        icon("search", 20),
        h("span", { text: "What do you want to do?" }),
        h("kbd", { text: navigator.platform.startsWith("Mac") ? "⌘K" : "Ctrl K" }),
      ),
    ),
    rise(h("div", { class: "stats" }, Object.values(stats).map((item) => item.element))),
    h("div", { class: "home-health" }, health.map((item) => item.element)),
    h("section", { class: "block" }, sectionHead("Jump in"), rise(h("div", { class: "task-grid" }, tasks))),
    h("section", { class: "block" }, sectionHead("Recent activity"), recent),
  );

  function loadStats() {
    stale = false;
    const fail = (item) => () => item.set("—", "Unavailable right now");
    software().then((catalog) => stats.apps.set(catalog.apps.filter((app) => app.installed).length, `of ${catalog.apps.length} in the catalog`), fail(stats.apps));
    query(["devops", "repos", "list", "--json"]).then(({ json }) => {
      const repos = Array.isArray(json) ? json : [];
      const changed = repos.filter((repo) => repo.state === "Changed").length;
      stats.projects.set(repos.length, changed ? `${changed} with changes` : "all clean");
    }, fail(stats.projects));
    query(["terminal", "summary", "--json"]).then(({ json }) => {
      const sessions = json?.sessions ?? [];
      // Only TUIOS says whether someone is looking at a session; for the others the tile names the multiplexer.
      stats.sessions.set(sessions.length, json?.backend === "tuios" ? `${sessions.filter((session) => session.attached).length} attached` : `on ${json?.backend}`);
    }, fail(stats.sessions));
    query(["agents", "status", "--json"]).then(({ json }) => {
      const agents = json?.agents ?? [];
      const working = agents.filter((agent) => agent.status === "working").length;
      stats.agents.set(agents.length, agents.length ? `${working} working` : "none running");
    }, fail(stats.agents));
    const paintHealth = (sections) =>
      health.forEach(({ key, mark }) => {
        mark.textContent = sections?.[key]?.summary ?? "Unavailable";
        mark.className = `pill ${HEALTH_TONES[sections?.[key]?.level] ?? ""}`;
      });
    query(["devops", "self", "status", "--shell", "--ssh", "--backup", "--json"]).then(({ json }) => paintHealth(json), () => paintHealth(null));
  }

  function showRecent() {
    const runs = activity.runs().sort((left, right) => right.started_at - left.started_at).slice(0, 6);
    if (runs.length === 0) {
      recent.replaceChildren(notice({ glyph: "clock", title: "Nothing yet", body: "The things you start will be listed here." }));
      return;
    }
    recent.replaceChildren(
      rise(
        h(
          "ul",
          { class: "run-list" },
          runs.map((run) =>
            h(
              "li",
              { class: "run-row", onclick: () => activity.reveal(run.id) },
              run.tile,
              h("strong", { text: run.title }),
              h("span", { class: `run-state ${run.exit_code === null ? "running" : run.exit_code === 0 ? "done" : "failed"}`, text: run.exit_code === null ? "Running" : run.exit_code === 0 ? "Finished" : "Had a problem" }),
              h("span", { class: "dim", text: `${formatClock(run.started_at)} · ${run.finished_at === null ? "in progress" : formatDuration(run.finished_at - run.started_at)}` }),
            ),
          ),
        ),
      ),
    );
  }

  on("runs", showRecent);
  on("data-stale", () => {
    stale = true;
    if (!element.hidden) loadStats();
  });
  showRecent();
  return { element, show: () => stale && loadStats() };
}
