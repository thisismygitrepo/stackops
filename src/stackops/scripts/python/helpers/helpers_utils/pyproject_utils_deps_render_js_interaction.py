DEPENDENCY_REPORT_JS_INTERACTION = """
  function connectControls() {
    const controls = document.querySelectorAll("[data-graph-action]");
    for (const control of controls) {
      if (control instanceof HTMLButtonElement) {
        control.addEventListener("click", () => runControlAction(control));
      }
    }
  }

  function runControlAction(control) {
    const action = control.dataset.graphAction || "";
    if (action === "fit") {
      fitViewBox();
    } else if (action === "reset") {
      resetLayout();
    } else if (action === "toggle-cycles") {
      cycleFocusEnabled = !cycleFocusEnabled;
      if (figureElement !== null) {
        figureElement.classList.toggle("cycle-focus", cycleFocusEnabled);
      }
      control.setAttribute("aria-pressed", String(cycleFocusEnabled));
    } else if (action === "move-left") {
      moveSelectedNode(-moveStep, 0);
    } else if (action === "move-right") {
      moveSelectedNode(moveStep, 0);
    } else if (action === "move-up") {
      moveSelectedNode(0, -moveStep);
    } else if (action === "move-down") {
      moveSelectedNode(0, moveStep);
    }
  }

  function handleKeyboardMove(event) {
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      moveSelectedNode(-moveStep, 0);
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      moveSelectedNode(moveStep, 0);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      moveSelectedNode(0, -moveStep);
    } else if (event.key === "ArrowDown") {
      event.preventDefault();
      moveSelectedNode(0, moveStep);
    }
  }

  function moveSelectedNode(deltaX, deltaY) {
    const selectedNode = ensureSelectedNode();
    if (selectedNode === null) {
      return;
    }
    selectedNode.x += deltaX;
    selectedNode.y += deltaY;
    updateGraph();
  }

  function ensureSelectedNode() {
    if (selectedNodeName === null && nodes.length > 0) {
      selectedNodeName = nodes[0].name;
    }
    return selectedNodeName === null ? null : nodeByName.get(selectedNodeName) || null;
  }

  function selectNode(nodeName) {
    selectedNodeName = nodeName;
    updateSelectionState();
    svgElement.focus();
  }

  function updateSelectionState() {
    for (const [nodeName, group] of nodeGroups) {
      group.classList.toggle("is-selected", nodeName === selectedNodeName);
    }
    if (selectionElement !== null) {
      selectionElement.value = selectedNodeName === null ? "No module selected" : `Selected: ${selectedNodeName}`;
      selectionElement.textContent = selectionElement.value;
    }
  }

  function startDrag(event, node) {
    if (event.button !== 0) {
      return;
    }
    selectNode(node.name);
    const point = svgPoint(event);
    dragState = { node, offsetX: point.x - node.x, offsetY: point.y - node.y };
    svgElement.setPointerCapture(event.pointerId);
  }

  function handlePointerMove(event) {
    if (dragState === null) {
      return;
    }
    const point = svgPoint(event);
    dragState.node.x = point.x - dragState.offsetX;
    dragState.node.y = point.y - dragState.offsetY;
    updateGraph();
  }

  function endDrag(event) {
    if (dragState === null) {
      return;
    }
    if (svgElement.hasPointerCapture(event.pointerId)) {
      svgElement.releasePointerCapture(event.pointerId);
    }
    dragState = null;
  }

  function resetLayout() {
    for (const node of nodes) {
      node.x = node.originalX;
      node.y = node.originalY;
    }
    updateGraph();
    fitViewBox();
  }

  function fitViewBox() {
    if (nodes.length === 0) {
      svgElement.setAttribute("viewBox", `0 0 ${emptyGraphWidth} ${emptyGraphHeight}`);
      return;
    }
    const bounds = graphBounds();
    svgElement.setAttribute("viewBox", `${bounds.x} ${bounds.y} ${bounds.width} ${bounds.height}`);
  }

  function graphBounds() {
    const minX = Math.min(...nodes.map((node) => node.x)) - graphPadding;
    const minY = Math.min(...nodes.map((node) => node.y)) - graphPadding;
    const maxX = Math.max(...nodes.map((node) => node.x + nodeWidth)) + graphPadding;
    const maxY = Math.max(...nodes.map((node) => node.y + nodeHeight)) + graphPadding;
    return { x: minX, y: minY, width: Math.max(emptyGraphWidth, maxX - minX), height: Math.max(emptyGraphHeight, maxY - minY) };
  }

  function svgPoint(event) {
    const point = svgElement.createSVGPoint();
    point.x = event.clientX;
    point.y = event.clientY;
    const transform = svgElement.getScreenCTM();
    if (transform === null) {
      return { x: 0, y: 0 };
    }
    const transformed = point.matrixTransform(transform.inverse());
    return { x: transformed.x, y: transformed.y };
  }
"""
