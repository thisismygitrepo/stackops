DEPENDENCY_REPORT_JS_SVG = """
  function initializeSvg() {
    svgElement.replaceChildren();
    const defs = createSvgElement("defs", "");
    const marker = createSvgElement("marker", "");
    marker.setAttribute("id", "dependency-arrow");
    marker.setAttribute("markerWidth", "12");
    marker.setAttribute("markerHeight", "12");
    marker.setAttribute("refX", "10");
    marker.setAttribute("refY", "6");
    marker.setAttribute("orient", "auto");
    marker.setAttribute("markerUnits", "strokeWidth");
    const arrowPath = createSvgElement("path", "");
    arrowPath.setAttribute("d", "M 1 1 L 11 6 L 1 11 z");
    marker.append(arrowPath);
    defs.append(marker);
    svgElement.append(defs, edgeLayer, nodeLayer);
    svgElement.addEventListener("keydown", handleKeyboardMove);
    svgElement.addEventListener("pointermove", handlePointerMove);
    svgElement.addEventListener("pointerup", endDrag);
    svgElement.addEventListener("pointercancel", endDrag);
  }

  function renderGraph() {
    edgeLayer.replaceChildren();
    nodeLayer.replaceChildren();
    edgePaths.clear();
    nodeGroups.clear();
    if (nodes.length === 0) {
      renderEmptyGraph();
      return;
    }
    for (const edge of edges) {
      const path = createSvgElement("path", cycleEdges.has(edgeKey(edge)) ? "edge is-cycle-edge" : "edge");
      path.setAttribute("marker-end", "url(#dependency-arrow)");
      edgeLayer.append(path);
      edgePaths.set(edgeKey(edge), path);
    }
    for (const node of nodes) {
      const group = createSvgElement("g", cycleNodes.has(node.name) ? "node is-cycle" : "node");
      group.setAttribute("tabindex", "0");
      group.dataset.nodeName = node.name;
      const rect = createSvgElement("rect", "");
      rect.setAttribute("width", String(nodeWidth));
      rect.setAttribute("height", String(nodeHeight));
      rect.setAttribute("rx", "8");
      const title = createSvgElement("title", "");
      title.textContent = node.path.length > 0 ? `${node.name}\\n${node.path}` : node.name;
      const primary = createSvgElement("text", "node-label");
      primary.setAttribute("x", "12");
      primary.setAttribute("y", "20");
      primary.textContent = shorten(node.name, 34);
      const secondary = createSvgElement("text", "node-path");
      secondary.setAttribute("x", "12");
      secondary.setAttribute("y", "38");
      secondary.textContent = shorten(node.path, 38);
      group.append(rect, title, primary, secondary);
      group.addEventListener("click", () => selectNode(node.name));
      group.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          selectNode(node.name);
        }
      });
      group.addEventListener("pointerdown", (event) => startDrag(event, node));
      nodeLayer.append(group);
      nodeGroups.set(node.name, group);
    }
    updateGraph();
  }

  function renderEmptyGraph() {
    const text = createSvgElement("text", "empty-graph");
    text.setAttribute("x", "40");
    text.setAttribute("y", "80");
    text.textContent = "No modules in this report.";
    nodeLayer.append(text);
    svgElement.setAttribute("viewBox", `0 0 ${emptyGraphWidth} ${emptyGraphHeight}`);
  }

  function updateGraph() {
    for (const edge of edges) {
      const path = edgePaths.get(edgeKey(edge));
      if (path !== undefined) {
        path.setAttribute("d", buildEdgePath(edge));
      }
    }
    for (const node of nodes) {
      const group = nodeGroups.get(node.name);
      if (group !== undefined) {
        group.setAttribute("transform", `translate(${node.x} ${node.y})`);
      }
    }
    updateSelectionState();
  }

  function buildEdgePath(edge) {
    const importer = nodeByName.get(edge.importer);
    const imported = nodeByName.get(edge.imported);
    if (importer === undefined || imported === undefined) {
      return "";
    }
    const startX = importer.x + nodeWidth;
    const startY = importer.y + nodeHeight / 2;
    const endX = imported.x;
    const endY = imported.y + nodeHeight / 2;
    const direction = endX >= startX ? 1 : -1;
    const curveSize = Math.max(44, Math.abs(endX - startX) / 2);
    return `M ${startX} ${startY} C ${startX + curveSize * direction} ${startY}, ${endX - curveSize * direction} ${endY}, ${endX} ${endY}`;
  }
"""
