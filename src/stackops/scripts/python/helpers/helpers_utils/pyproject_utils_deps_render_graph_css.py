DEPENDENCY_REPORT_GRAPH_CSS = """
.dependency-figure {
  margin: 12px 0 18px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--panel);
  overflow: hidden;
}
.dependency-figure figcaption {
  padding: 11px 12px 0;
  color: var(--muted);
  font-size: 12px;
  font-weight: 600;
}
.graph-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 10px 12px 12px;
  border-bottom: 1px solid var(--border);
}
.graph-actions, .graph-nudge {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
button {
  min-width: 36px;
  min-height: 32px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--button);
  color: var(--fg);
  font: inherit;
  font-size: 12px;
  cursor: pointer;
}
button:hover, button:focus-visible {
  background: var(--button-hover);
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}
button[aria-pressed="true"] {
  border-color: var(--accent);
  color: var(--accent-strong);
}
#graph-selection {
  min-width: 220px;
  color: var(--muted);
  font-size: 12px;
  overflow-wrap: anywhere;
}
#dependency-graph {
  display: block;
  width: 100%;
  height: min(72vh, 760px);
  min-height: 420px;
  background:
    linear-gradient(90deg, color-mix(in srgb, var(--border) 35%, transparent) 1px, transparent 1px),
    linear-gradient(color-mix(in srgb, var(--border) 35%, transparent) 1px, transparent 1px);
  background-size: 32px 32px;
  touch-action: none;
}
#dependency-graph:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: -2px;
}
.edge {
  fill: none;
  stroke: var(--edge);
  stroke-width: 1.6;
  opacity: 0.74;
}
marker path {
  fill: var(--edge);
}
.node {
  cursor: grab;
  user-select: none;
}
.node:active {
  cursor: grabbing;
}
.node rect {
  fill: var(--node);
  stroke: var(--border);
  stroke-width: 1.2;
  filter: drop-shadow(0 2px 4px rgb(0 0 0 / 0.12));
}
.node.is-cycle rect {
  fill: color-mix(in srgb, var(--danger) 12%, var(--node));
  stroke: var(--danger);
}
.node.is-selected rect {
  stroke: var(--accent);
  stroke-width: 2.4;
}
.node-label {
  fill: var(--fg);
  font-size: 12px;
  font-weight: 650;
}
.node-path {
  fill: var(--muted);
  font-size: 10px;
}
.empty-graph {
  fill: var(--muted);
  font-size: 14px;
}
.cycle-focus .node:not(.is-cycle) {
  opacity: 0.24;
}
.cycle-focus .edge:not(.is-cycle-edge) {
  opacity: 0.1;
}
"""
