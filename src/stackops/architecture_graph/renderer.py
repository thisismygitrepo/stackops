import json
from importlib.resources import files
from pathlib import Path

from stackops.architecture_graph.models import GraphPagePayload


def render_html(payload: GraphPagePayload) -> str:
    css_text = read_package_text("graph_css.txt") + read_package_text("graph_css_continued.txt")
    javascript_text = read_package_text("graph_js.txt") + read_package_text("graph_js_continued.txt")
    payload_json = json.dumps(payload, indent=2, sort_keys=True).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>StackOps Dependency Graph</title>
  <style>
{css_text}
  </style>
</head>
<body>
  <header class="topbar">
    <div>
      <p class="eyebrow">StackOps Architecture</p>
      <h1>Dependency Graph</h1>
    </div>
    <dl class="stats">
      <div><dt>Nodes</dt><dd id="node-count">0</dd></div>
      <div><dt>Edges</dt><dd id="edge-count">0</dd></div>
      <div><dt>Modules</dt><dd id="module-count">0</dd></div>
    </dl>
  </header>
  <main class="layout">
    <section class="graph-panel" aria-label="Dependency graph">
      <div class="toolbar">
        <input id="search" type="search" placeholder="Filter modules" autocomplete="off">
        <label class="depth-field" for="depth-select">
          <span>Depth</span>
          <select id="depth-select"></select>
        </label>
        <button id="toggle-bidi" type="button" aria-pressed="false">Bidirectional</button>
        <button id="reset" type="button">Reset</button>
      </div>
      <svg id="graph" role="img" aria-label="StackOps dependency graph"></svg>
    </section>
    <aside class="details" aria-label="Selected dependency details">
      <div class="details-head">
        <p class="eyebrow">Selection</p>
        <h2 id="detail-title">Dependency Graph</h2>
        <p id="detail-meta">No module selected</p>
      </div>
      <div class="legend" id="legend"></div>
      <section>
        <h3>Imports</h3>
        <ul id="outgoing-list" class="edge-list"></ul>
      </section>
      <section>
        <h3>Imported By</h3>
        <ul id="incoming-list" class="edge-list"></ul>
      </section>
    </aside>
  </main>
  <script id="graph-data" type="application/json">
{payload_json}
  </script>
  <script>
{javascript_text}
  </script>
</body>
</html>
"""


def write_html(payload: GraphPagePayload, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_html(payload), encoding="utf-8")
    return output_path


def read_package_text(file_name: str) -> str:
    return files("stackops.architecture_graph").joinpath(file_name).read_text(encoding="utf-8")
