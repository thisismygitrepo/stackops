import { h, icon } from "./dom.js";
import { SERIES } from "./presets.js";
import { nodeHash, state } from "./state.js";

const ROOT_ID = "stackops";
const NEUTRAL_FILL = { light: "#c3c2b7", dark: "#52514e" };
const DARK_INK_FILLS = new Set(["#eda100", "#c3c2b7"]);
const FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif';
const VIEWS = [["sunburst", "Sunburst"], ["treemap", "Treemap"], ["icicle", "Icicle"]];
let chartLibrary = null;

function loadChartLibrary() {
  chartLibrary ??= new Promise((resolve, reject) => {
    const script = h("script", { src: "/vendor/plotly.min.js" });
    script.addEventListener("load", () => resolve(window.Plotly));
    script.addEventListener("error", () => {
      chartLibrary = null;
      script.remove();
      reject(new Error("The chart library could not be loaded. It is downloaded once, on first use: check the connection and try again."));
    });
    document.head.append(script);
  });
  return chartLibrary;
}

export function createMapView() {
  const { tree } = state.boot;
  const darkScheme = matchMedia("(prefers-color-scheme: dark)");
  const plot = h("div");
  const plotHolder = h("div", { class: "map-plot" }, plot);
  const side = h("aside", { class: "map-side" });
  const legend = h("div", { class: "map-legend" });
  let view = "sunburst";
  let levels = 3;
  let drawn = null;
  let wired = false;

  const viewButtons = VIEWS.map(([value, label]) =>
    h("button", {
      text: label,
      onclick: () => {
        view = value;
        draw();
      },
    }),
  );
  const levelSelect = h(
    "select",
    {
      class: "select",
      onchange: () => {
        levels = Number(levelSelect.value);
        draw();
      },
    },
    [["2", "2 levels"], ["3", "3 levels"], ["4", "4 levels"], ["-1", "All levels"]].map(([value, label]) => h("option", { value, text: label })),
  );
  levelSelect.value = String(levels);

  function describe(node) {
    const isGroup = node.kind !== "command";
    side.replaceChildren(
      h("span", { class: "glyph", text: node.icon || (isGroup ? "🗂️" : "▫️") }),
      h("h2", { text: `stackops ${node.path}`.trim() }),
      h("p", { text: node.description.trim() || node.summary }),
      h(
        "dl",
        {},
        h("dt", { text: "Kind" }),
        h("dd", { text: isGroup ? "group" : "command" }),
        node.short_path && h("dt", { text: "Alias" }),
        node.short_path && h("dd", { text: `stackops ${node.short_path}` }),
        isGroup && h("dt", { text: "Commands" }),
        isGroup && h("dd", { text: String(node.leaves) }),
      ),
      h("a", { class: "button primary", href: nodeHash(node) }, isGroup ? "Open group" : "Open command", icon("arrow", 14)),
      h("p", { class: "hint", text: "Click a group to zoom into it, the centre to zoom back out, and a command to open its form." }),
    );
  }

  async function draw() {
    const scheme = darkScheme.matches ? "dark" : "light";
    const styles = getComputedStyle(document.documentElement);
    const token = (name) => styles.getPropertyValue(name).trim();
    const inkOf = (fill) => (DARK_INK_FILLS.has(fill) ? "#0b0b0b" : "#ffffff");
    const ids = [];
    const labels = [];
    const parents = [];
    const values = [];
    const fills = [];
    const inks = [];
    const details = [];
    const visit = (node, parentId, fill, ink) => {
      const id = node.path || ROOT_ID;
      ids.push(id);
      labels.push(node.name);
      parents.push(parentId);
      values.push(node.leaves);
      fills.push(fill);
      inks.push(ink);
      details.push([`stackops ${node.path}`.trim(), node.summary]);
      node.children.forEach((child, index) => {
        const childFill = node.kind === "root" ? (SERIES[scheme][index] ?? NEUTRAL_FILL[scheme]) : fill;
        visit(child, id, childFill, node.kind === "root" ? inkOf(childFill) : ink);
      });
    };
    visit(tree, "", token("--raised"), token("--text"));
    legend.replaceChildren(
      ...tree.children.map((child, index) =>
        h("a", { href: nodeHash(child), title: child.summary }, h("i", { style: `background: ${SERIES[scheme][index] ?? NEUTRAL_FILL[scheme]}` }), child.name),
      ),
    );
    viewButtons.forEach((button, index) => button.setAttribute("aria-pressed", String(VIEWS[index][0] === view)));
    const trace = {
      type: view, ids, labels, parents, values, branchvalues: "total", sort: false, maxdepth: levels, customdata: details, textinfo: "label",
      marker: { colors: fills, line: { color: token("--surface"), width: 2 } },
      textfont: { family: FONT, size: 12.5, color: inks },
      hovertemplate: "<b>%{customdata[0]}</b><br>%{customdata[1]}<extra></extra>",
      ...(view === "sunburst" ? { insidetextorientation: "radial", leaf: { opacity: 1 } } : {}),
      ...(view === "icicle" ? { leaf: { opacity: 1 }, tiling: { orientation: "h" } } : {}),
      ...(view === "sunburst" ? {} : { pathbar: { visible: true, textfont: { family: FONT, size: 12 } } }),
    };
    const layout = {
      margin: { l: 16, r: 16, t: 16, b: 16 }, paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
      font: { family: FONT, size: 13, color: token("--text") }, uniformtext: { minsize: 10, mode: "hide" },
      hoverlabel: { bgcolor: token("--surface"), bordercolor: token("--hairline"), align: "left", font: { family: FONT, size: 12.5, color: token("--text") } },
    };
    try {
      const Plotly = await loadChartLibrary();
      await Plotly.react(plot, [trace], layout, { displayModeBar: false, responsive: true });
      drawn = scheme;
      if (wired) return;
      wired = true;
      const nodeOf = (event) => state.nodes.get(event.points[0].id === ROOT_ID ? "" : event.points[0].id);
      plot.on("plotly_hover", (event) => describe(nodeOf(event)));
      for (const name of ["plotly_sunburstclick", "plotly_treemapclick", "plotly_icicleclick"]) {
        plot.on(name, (event) => {
          const node = nodeOf(event);
          describe(node);
          if (node.kind !== "command") return true;
          location.hash = nodeHash(node);
          return false;
        });
      }
      new ResizeObserver(() => !element.hidden && Plotly.Plots.resize(plot)).observe(plotHolder);
    } catch (error) {
      plotHolder.replaceChildren(h("div", { class: "panel-state" }, h("h2", { text: "The command map could not be drawn" }), h("p", { text: error.message })));
    }
  }

  const element = h(
    "section",
    { class: "map" },
    h(
      "div",
      { class: "map-main" },
      h("div", { class: "map-bar" }, h("div", { class: "segmented", role: "group", "aria-label": "Chart type" }, viewButtons), h("label", {}, "Depth", levelSelect), legend),
      plotHolder,
    ),
    side,
  );
  describe(tree);
  darkScheme.addEventListener("change", () => !element.hidden && draw());

  function show() {
    if (drawn !== (darkScheme.matches ? "dark" : "light")) draw();
    return [{ label: "Command map" }];
  }

  return { element, show };
}
