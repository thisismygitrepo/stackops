DEPENDENCY_REPORT_JS_SHARED = """
  function readNode(value) {
    const item = typeof value === "object" && value !== null ? value : {};
    const name = typeof item.name === "string" ? item.name : "";
    const path = typeof item.path === "string" ? item.path : "";
    return { name, path, x: 0, y: 0, originalX: 0, originalY: 0 };
  }

  function readEdge(value) {
    const item = typeof value === "object" && value !== null ? value : {};
    const importer = typeof item.importer === "string" ? item.importer : "";
    const imported = typeof item.imported === "string" ? item.imported : "";
    return { importer, imported };
  }

  function edgeKey(edge) {
    return `${edge.importer}\\u0000${edge.imported}`;
  }

  function createSvgElement(tagName, className) {
    const element = document.createElementNS(svgNamespace, tagName);
    if (className.length > 0) {
      element.setAttribute("class", className);
    }
    return element;
  }

  function shorten(value, maxLength) {
    if (value.length <= maxLength) {
      return value;
    }
    const leftLength = Math.floor((maxLength - 3) / 2);
    const rightLength = maxLength - 3 - leftLength;
    return `${value.slice(0, leftLength)}...${value.slice(value.length - rightLength)}`;
  }
"""
