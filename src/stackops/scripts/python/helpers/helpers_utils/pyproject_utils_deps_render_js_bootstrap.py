DEPENDENCY_REPORT_JS_BOOTSTRAP = """
(() => {
  const svgNamespace = "http://www.w3.org/2000/svg";
  const nodeWidth = 230;
  const nodeHeight = 48;
  const columnGap = 88;
  const rowGap = 28;
  const graphPadding = 36;
  const moveStep = 24;
  const emptyGraphWidth = 860;
  const emptyGraphHeight = 320;
  const dataElement = document.getElementById("dependency-report");
  const svgElement = document.getElementById("dependency-graph");
  const figureElement = document.getElementById("dependency-figure");
  const selectionElement = document.getElementById("graph-selection");
  if (dataElement === null || !(svgElement instanceof SVGSVGElement)) {
    return;
  }

  const report = JSON.parse(dataElement.textContent || "{}");
  const rawNodes = Array.isArray(report.nodes) ? report.nodes : [];
  const rawEdges = Array.isArray(report.edges) ? report.edges : [];
  const rawCycleGroups = Array.isArray(report.cycle_groups) ? report.cycle_groups : [];
  const nodes = rawNodes.map(readNode).filter((node) => node.name.length > 0).sort((left, right) => left.name.localeCompare(right.name));
  const nodeByName = new Map(nodes.map((node) => [node.name, node]));
  const edges = rawEdges.map(readEdge).filter((edge) => nodeByName.has(edge.importer) && nodeByName.has(edge.imported));
  const cycleNodes = new Set();
  for (const group of rawCycleGroups) {
    if (Array.isArray(group)) {
      for (const nodeName of group) {
        if (typeof nodeName === "string") {
          cycleNodes.add(nodeName);
        }
      }
    }
  }
  const cycleEdges = new Set(edges.filter((edge) => cycleNodes.has(edge.importer) && cycleNodes.has(edge.imported)).map(edgeKey));
  let selectedNodeName = nodes.length > 0 ? nodes[0].name : null;
  let dragState = null;
  let cycleFocusEnabled = false;
  const edgePaths = new Map();
  const nodeGroups = new Map();
  const edgeLayer = createSvgElement("g", "edges");
  const nodeLayer = createSvgElement("g", "nodes");

  initializeSvg();
  applyInitialLayout();
  renderGraph();
  fitViewBox();
  connectControls();
  updateSelectionState();
"""
