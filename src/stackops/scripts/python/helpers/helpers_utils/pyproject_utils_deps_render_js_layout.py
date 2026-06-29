DEPENDENCY_REPORT_JS_LAYOUT = """
  function applyInitialLayout() {
    if (nodes.length === 0) {
      return;
    }
    const levels = computeLevels();
    const groupedNodes = new Map();
    let maxLevel = 0;
    for (const node of nodes) {
      const level = levels.get(node.name) || 0;
      maxLevel = Math.max(maxLevel, level);
      const group = groupedNodes.get(level) || [];
      group.push(node);
      groupedNodes.set(level, group);
    }
    for (let level = 0; level <= maxLevel; level += 1) {
      const group = groupedNodes.get(level) || [];
      group.sort((left, right) => left.name.localeCompare(right.name));
      for (let row = 0; row < group.length; row += 1) {
        const node = group[row];
        node.x = graphPadding + level * (nodeWidth + columnGap);
        node.y = graphPadding + row * (nodeHeight + rowGap);
        node.originalX = node.x;
        node.originalY = node.y;
      }
    }
  }

  function computeLevels() {
    const levels = new Map(nodes.map((node) => [node.name, 0]));
    const indegrees = new Map(nodes.map((node) => [node.name, 0]));
    const outgoing = new Map(nodes.map((node) => [node.name, []]));
    for (const edge of edges) {
      outgoing.get(edge.importer).push(edge.imported);
      indegrees.set(edge.imported, (indegrees.get(edge.imported) || 0) + 1);
    }
    const queue = nodes.map((node) => node.name).filter((nodeName) => (indegrees.get(nodeName) || 0) === 0).sort();
    const visited = new Set();
    while (queue.length > 0) {
      const nodeName = queue.shift();
      visited.add(nodeName);
      for (const importedName of outgoing.get(nodeName) || []) {
        levels.set(importedName, Math.max(levels.get(importedName) || 0, (levels.get(nodeName) || 0) + 1));
        indegrees.set(importedName, (indegrees.get(importedName) || 0) - 1);
        if ((indegrees.get(importedName) || 0) === 0) {
          queue.push(importedName);
          queue.sort();
        }
      }
    }
    if (visited.size === 0 && nodes.length > 0) {
      const rowsPerColumn = Math.max(1, Math.ceil(Math.sqrt(nodes.length)));
      for (let index = 0; index < nodes.length; index += 1) {
        levels.set(nodes[index].name, Math.floor(index / rowsPerColumn));
      }
    }
    return levels;
  }
"""
