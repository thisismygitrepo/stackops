const SECTION_RENDERERS = {
  apps: renderApps, repos: renderRepos, backup: renderBackup, configs: renderConfigs, system: renderSystem, shell: renderShell, ssh: renderSsh,
};
const sections = Object.entries(report.sections).map(([id, snapshot]) => ({ id, title: report.titles[id], ...snapshot }));
const views = new Map();

const masthead = el("header", "masthead");
masthead.append(el("h1", "", "StackOps status"));
const machine = report.sections.system?.details;
if (machine?.hostname) masthead.append(el("span", "meta", `${machine.user}@${machine.hostname}`));
const hint = el("span", "hint");
hint.append(el("kbd", "", "j"), " ", el("kbd", "", "k"), " next / previous section");
masthead.append(el("span", "meta", `Generated ${report.generated_at}`), hint);

const tabs = el("nav", "tabs");
tabs.setAttribute("aria-label", "Sections");
const overviewTab = el("a", "", "Overview");
overviewTab.href = "#overview";
overviewTab.dataset.section = "overview";
tabs.append(overviewTab);
const cards = el("div", "cards");
const overview = el("section", "panel");
overview.append(cards);
views.set("overview", overview);
const main = el("main");
main.append(overview);
for (const section of sections) {
  const tone = LEVEL_TONES[section.level];
  const tab = el("a");
  tab.href = `#${section.id}`;
  tab.dataset.section = section.id;
  tab.append(mark(tone), section.title);
  tabs.append(tab);

  const card = el("a", "card");
  card.href = `#${section.id}`;
  card.append(el("span", "card-title", section.title), statusLabel(tone, section.level), el("span", "card-summary", section.summary));
  cards.append(card);

  const panel = el("section", "panel");
  const head = el("header", "panel-head");
  head.append(el("h2", "", section.title), statusLabel(tone, section.level), el("span", "meta", section.summary));
  panel.append(head);
  if (typeof section.details.error === "string") panel.append(el("p", "notice", `This check could not be completed (${section.details.error}).`));
  if (Object.keys(section.details).some((key) => key !== "error")) panel.append(...SECTION_RENDERERS[section.id](section.details));
  views.set(section.id, panel);
  main.append(panel);
}
document.getElementById("app").append(masthead, tabs, main);

function currentView() {
  const id = location.hash.slice(1);
  if (views.has(id)) return id;
  return sections.length === 1 ? sections[0].id : "overview";
}

function render() {
  const current = currentView();
  for (const [id, view] of views) view.hidden = id !== current;
  for (const tab of tabs.children) tab.setAttribute("aria-current", String(tab.dataset.section === current));
  window.scrollTo(0, 0);
}

window.addEventListener("hashchange", render);
document.addEventListener("keydown", (event) => {
  if (event.target instanceof HTMLInputElement || event.metaKey || event.ctrlKey || event.altKey) return;
  if (event.key !== "j" && event.key !== "k") return;
  const order = [...views.keys()];
  location.hash = `#${order[(order.indexOf(currentView()) + (event.key === "j" ? 1 : order.length - 1)) % order.length]}`;
});
render();
