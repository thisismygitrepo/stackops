import { h, toast } from "/assets/scripts/dom.js";
import { api, initState } from "/assets/scripts/state.js";
import { createActivity } from "./activity.js";
import { SPACES, VIEW_KEY } from "./catalog.js";
import { openFind } from "./find_sheet.js";
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
import { createSessionsSpace } from "./spaces/sessions.js";
import { createToolboxSpace } from "./spaces/toolbox.js";
import { createSpotlight } from "./spotlight.js";
import { createToolSheet } from "./tool_sheet.js";

function parseRoute() {
  const parts = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean).map(decodeURIComponent);
  const space = SPACES.find((candidate) => candidate.id === parts[0]);
  return { space: space?.id ?? "home", rest: parts.slice(1) };
}

async function start() {
  initState(await api.bootstrap());
  installPointerEffects();
  const spaces = {};
  const openReport = (report) => spaces.reports.openAdHoc(report);
  const activity = createActivity({ openReport });
  const tools = createToolSheet({ activity, openReport, guides: { seek: () => openFind({ activity }) } });
  const spotlight = createSpotlight({ tools });
  const context = { activity, tools, openReport, openSearch: spotlight.open };
  Object.assign(spaces, {
    home: createHomeSpace(context),
    apps: createAppsSpace(context),
    projects: createProjectsSpace(context),
    sessions: createSessionsSpace(context),
    agents: createAgentsSpace(context),
    dotfiles: createDotfilesSpace(context),
    data: createDataSpace(context),
    network: createNetworkSpace(context),
    machine: createMachineSpace(context),
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

if (localStorage.getItem(VIEW_KEY) === "dev") location.replace("/dev");
else {
  start().catch((error) => {
    document.getElementById("app").replaceChildren(h("p", { class: "boot-note", text: `StackOps could not start: ${error.message}` }));
  });
}
