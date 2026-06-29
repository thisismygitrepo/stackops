DEPENDENCY_REPORT_CSS = """
:root {
  color-scheme: light dark;
  --bg: #f7f7f4;
  --fg: #1f2428;
  --muted: #5b646b;
  --border: #cfd6dc;
  --accent: #1d6f78;
  --danger: #9f2d35;
  --table: #ffffff;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #111315;
    --fg: #e7ecef;
    --muted: #a8b0b7;
    --border: #384148;
    --accent: #77c7d2;
    --danger: #ff8a96;
    --table: #171b1f;
  }
}
body {
  margin: 0;
  background: var(--bg);
  color: var(--fg);
  font: 14px/1.45 ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
main {
  max-width: 1180px;
  margin: 0 auto;
  padding: 28px;
}
h1 {
  margin: 0 0 6px;
  font-size: 24px;
  letter-spacing: 0;
}
h2 {
  margin: 26px 0 10px;
  font-size: 16px;
  letter-spacing: 0;
}
.summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
  margin: 18px 0;
}
.metric {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px;
  background: var(--table);
}
.metric span {
  display: block;
  color: var(--muted);
  font-size: 12px;
}
.metric strong {
  display: block;
  margin-top: 4px;
  font-size: 20px;
}
.meta {
  color: var(--muted);
  overflow-wrap: anywhere;
}
table {
  width: 100%;
  border-collapse: collapse;
  background: var(--table);
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
}
th, td {
  padding: 9px 10px;
  border-bottom: 1px solid var(--border);
  text-align: left;
  vertical-align: top;
  overflow-wrap: anywhere;
}
th {
  color: var(--muted);
  font-size: 12px;
  font-weight: 600;
}
tr:last-child td {
  border-bottom: 0;
}
code {
  color: var(--accent);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
}
.danger code {
  color: var(--danger);
}
script {
  display: none;
}
"""
