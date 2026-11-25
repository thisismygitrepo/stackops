import { h, icon } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { query, software, staleKeeper } from "../data.js";
import { partLoaders } from "../features.js";
import { createHeroOrbit } from "../hero_orbit.js";
import { rise } from "../motion.js";
import { createParts } from "../space_kit.js";
import { pill, stat } from "../widgets.js";
import { greeting } from "../words.js";
import { createOverview } from "./settings/overview.js";

// The parts of the CLI's health check the four counts do not already cover, and the page that deals with each.
// A design choice: managed settings are left out, since that part alone takes several seconds and Dotfiles shows it.
const HEALTH = [["shell", "Shell profile", "#/reports/status"], ["ssh", "SSH", "#/network"], ["backup", "Backups", "#/data"]];
const HEALTH_TONES = { ready: "good", attention: "warn", error: "bad" };

// Home, at #/: how this machine stands, then its StackOps settings (settings/overview.js). The settings tools have no page of their own, so
// the views the Settings feature list names (feature_lists/settings.js) swap in here, each at an address under #/home: the settings files,
// the guided setup, the setup scripts and the packaged files.
export function createHomeSpace(context) {
  const { boot } = state;
  const name = boot.user.charAt(0).toUpperCase() + boot.user.slice(1);
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
  const settings = createOverview(context);

  const front = h(
    "div",
    { class: "home" },
    h(
      "header",
      { class: "hero" },
      createHeroOrbit(),
      h("span", { class: "overline", text: `${boot.host} · ${boot.platform}` }),
      h("h1", {}, `${greeting()}, `, h("em", { text: name })),
      h("p", { text: "Your machine, apps, projects, and agents — one click away." }),
      h(
        "button",
        { class: "hero-search", type: "button", onclick: () => context.openSearch() },
        icon("search", 20),
        h("span", { text: "What do you want to do?" }),
        h("kbd", { text: navigator.platform.startsWith("Mac") ? "⌘K" : "Ctrl K" }),
      ),
    ),
    rise(h("div", { class: "stats" }, Object.values(stats).map((item) => item.element))),
    h("div", { class: "home-health" }, health.map((item) => item.element)),
    settings.element,
  );
  const element = h("section", { class: "view", hidden: true }, front);

  function loadStats() {
    // A design choice: a count that did not load marks the page stale again, so the next visit asks once more. Only the commands that failed run
    // then, since the answers that arrived are kept. On a machine where one always fails, that command runs on every visit to Home.
    const fail = (item) => () => {
      keeper.spoil();
      item.set("—", "Unavailable right now");
    };
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
    query(["devops", "self", "status", "--shell", "--ssh", "--backup", "--json"]).then(({ json }) => paintHealth(json), () => {
      keeper.spoil();
      paintHealth(null);
    });
  }

  // The counts are kept against the overview, not the page: while one of the settings views is shown they wait for the next visit.
  const keeper = staleKeeper(front, loadStats);
  const overview = {
    element: front,
    show() {
      keeper.ensure();
      settings.show();
    },
  };
  return { element, show: createParts({ element, built: { "": overview }, loaders: partLoaders("home"), context }) };
}
