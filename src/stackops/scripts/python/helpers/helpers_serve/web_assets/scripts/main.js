import { createBrowseView } from "./browse_view.js";
import { createRail, createTopbar } from "./chrome.js";
import { createDashboardsView } from "./dashboards_view.js";
import { createDock } from "./dock.js";
import { h, toast } from "./dom.js";
import { createHomeView } from "./home_view.js";
import { createMapView } from "./map_view.js";
import { createPalette } from "./palette.js";
import { api, initState, parseRoute } from "./state.js";

async function start() {
  initState(await api.bootstrap());
  const dock = createDock();
  const dashboards = createDashboardsView({ dock });
  const views = {
    home: createHomeView({ dock }),
    browse: createBrowseView({ dock, openReport: dashboards.openAdHoc }),
    dashboards,
    map: createMapView(),
  };
  const palette = createPalette();
  const rail = createRail({ openPalette: palette.open });
  const topbar = createTopbar({ dock });
  const viewport = h("main", { class: "viewport" }, Object.values(views).map((view) => view.element));
  document.getElementById("app").replaceChildren(h("div", { class: "shell" }, rail.element, h("div", { class: "stage" }, topbar.element, viewport, dock.element)), palette.element);

  const render = () => {
    const route = parseRoute();
    for (const [name, view] of Object.entries(views)) view.element.hidden = name !== route.view;
    const crumbs = views[route.view].show(route);
    rail.setActive(route);
    topbar.setCrumbs(crumbs);
    viewport.scrollTop = 0;
    document.querySelector(".shell").classList.remove("rail-open");
    document.title = `${crumbs.at(-1).label} · StackOps`;
  };
  window.addEventListener("hashchange", render);
  window.addEventListener("unhandledrejection", (event) => toast(event.reason?.message ?? String(event.reason)));
  render();
  await dock.restore();
}

start().catch((error) => {
  document.getElementById("app").replaceChildren(h("p", { class: "boot-note", text: `StackOps could not start: ${error.message}` }));
});
