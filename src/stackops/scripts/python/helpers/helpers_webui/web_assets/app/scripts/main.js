import { h, toast } from "/assets/scripts/dom.js";
import { api, initState } from "/assets/scripts/state.js";
import { createActivity } from "./activity.js";
import { SPACES } from "./catalog.js";
import { createGuides } from "./features.js";
import { installPointerEffects, replay } from "./motion.js";
import { closeAll } from "./overlays.js";
import { createShell } from "./shell.js";
import { createAgentsSpace } from "./spaces/agents.js";
import { createAppsSpace } from "./spaces/apps.js";
import { createDataSpace } from "./spaces/data.js";
import { createDotfilesSpace } from "./spaces/dotfiles.js";
import { createHomeSpace } from "./spaces/home.js";
import { createMachineSpace } from "./spaces/machine.js";
import { createNetworkSpace } from "./spaces/network.js";
import { createProjectsSpace } from "./spaces/projects.js";
import { createReportsSpace } from "./spaces/reports.js";
import { createScriptsSpace } from "./spaces/scripts.js";
import { createSecuritySpace } from "./spaces/security.js";
import { createSessionsSpace } from "./spaces/sessions.js";
import { createToolboxSpace } from "./spaces/toolbox.js";
import { createVaultSpace } from "./spaces/vault.js";
import { createSpotlight } from "./spotlight.js";
import { createToolSheet } from "./tool_sheet.js";

function parseRoute() {
  let parts;
  try {
    parts = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean).map(decodeURIComponent);
  } catch {
    // The address is input from outside. One that cannot be decoded (cut off, or edited by hand) shows Home, as an unknown page does.
    parts = [];
  }
  const space = SPACES.find((candidate) => candidate.id === parts[0]);
  return { space: space?.id ?? "home", rest: parts.slice(1) };
}

async function start() {
  initState(await api.bootstrap());
  installPointerEffects();
  const spaces = {};
  const openReport = (report) => spaces.reports.openAdHoc(report);
  const activity = createActivity({ openReport });
  // Filled in once `context` exists: a purpose-built view is handed the same things a page is, the tool sheet among them.
  const guides = {};
  const tools = createToolSheet({ activity, openReport, guides });
  const spotlight = createSpotlight({ tools });
  const context = { activity, tools, openReport, openSearch: spotlight.open };
  Object.assign(guides, createGuides(context));
  Object.assign(spaces, {
    home: createHomeSpace(context),
    apps: createAppsSpace(context),
    projects: createProjectsSpace(context),
    sessions: createSessionsSpace(context),
    scripts: createScriptsSpace(context),
    agents: createAgentsSpace(context),
    dotfiles: createDotfilesSpace(context),
    data: createDataSpace(context),
    network: createNetworkSpace(context),
    machine: createMachineSpace(context),
    security: createSecuritySpace(context),
    vault: createVaultSpace(context),
    reports: createReportsSpace(context),
    tools: createToolboxSpace(context),
  });
  const shell = createShell({ openSearch: spotlight.open, activity });
  const stage = h("main", { class: "stage" }, Object.values(spaces).map((space) => space.element));
  document.getElementById("app").replaceChildren(
    h("div", { class: "aurora", "aria-hidden": "true" }, h("i"), h("i"), h("i")),
    h("div", { class: "frame" }, shell.rail, h("div", { class: "column" }, shell.topbar, stage)),
    activity.element,
  );

  let shown = null;
  const render = () => {
    closeAll();
    const route = parseRoute();
    for (const [id, space] of Object.entries(spaces)) space.element.hidden = id !== route.space;
    const space = spaces[route.space];
    space.show(route.rest);
    if (shown !== route.space) {
      replay(space.element, "enter");
      stage.scrollTop = 0;
    }
    shown = route.space;
    shell.setActive(route.space);
    document.title = `${SPACES.find((candidate) => candidate.id === route.space).title} · StackOps`;
  };
  window.addEventListener("hashchange", render);
  window.addEventListener("resize", () => shell.setActive(shown));
  window.addEventListener("unhandledrejection", (event) => toast(event.reason?.message ?? String(event.reason)));
  render();
  document.body.classList.add("booted");
  await activity.restore();
}

start().catch((error) => {
  document.getElementById("app").replaceChildren(h("p", { class: "boot-note failed", text: `StackOps could not start: ${error.message}` }));
});
