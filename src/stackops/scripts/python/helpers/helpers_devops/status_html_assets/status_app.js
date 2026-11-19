const SECTION_RENDERERS = {
  apps: renderApps, repos: renderRepos, backup: renderBackup, configs: renderConfigs, system: renderSystem, shell: renderShell, ssh: renderSsh,
};
const sections = Object.entries(report.sections).map(([id, snapshot]) => ({ id, title: report.titles[id], ...snapshot }));

const masthead = el("header", "masthead");
masthead.append(el("h1", "", "StackOps status"));
const machine = report.sections.system?.details;
if (machine?.hostname) masthead.append(el("span", "meta", `${machine.user}@${machine.hostname}`));
const hint = el("span", "hint");
hint.append(el("kbd", "", "j"), " ", el("kbd", "", "k"), " next / previous section");
masthead.append(el("span", "meta", `Generated ${report.generated_at}`), hint);

const jump = el("nav", "jump");
jump.setAttribute("aria-label", "Sections");
const cards = el("div", "cards");
const main = el("main");
main.append(cards);
for (const section of sections) {
  const tone = LEVEL_TONES[section.level];
  const link = el("a");
  link.href = `#${section.id}`;
  link.dataset.section = section.id;
  link.append(mark(tone), section.title);
  jump.append(link);

  const card = el("a", "card");
  card.href = `#${section.id}`;
  card.append(el("span", "card-title", section.title), statusLabel(tone, section.level), el("span", "card-summary", section.summary));
  cards.append(card);

  const panel = el("section", "panel");
  panel.id = section.id;
  const head = el("header", "panel-head");
  head.append(el("h2", "", section.title), statusLabel(tone, section.level), el("span", "meta", section.summary));
  panel.append(head);
  if (typeof section.details.error === "string") panel.append(el("p", "notice", `This check could not be completed (${section.details.error}).`));
  if (Object.keys(section.details).some((key) => key !== "error")) panel.append(...SECTION_RENDERERS[section.id](section.details));
  main.append(panel);
}
document.getElementById("app").append(masthead, jump, main);

function currentSection() {
  let current = sections[0].id;
  for (const section of sections) {
    if (document.getElementById(section.id).getBoundingClientRect().top <= 96) current = section.id;
  }
  return current;
}

function markCurrent() {
  const current = currentSection();
  for (const link of jump.children) link.setAttribute("aria-current", String(link.dataset.section === current));
}

window.addEventListener("scroll", markCurrent, { passive: true });
document.addEventListener("keydown", (event) => {
  if (event.target instanceof HTMLInputElement || event.metaKey || event.ctrlKey || event.altKey) return;
  if (event.key !== "j" && event.key !== "k") return;
  const index = sections.findIndex((section) => section.id === currentSection());
  const target = sections[Math.min(sections.length - 1, Math.max(0, index + (event.key === "j" ? 1 : -1)))];
  history.replaceState(null, "", `#${target.id}`);
  document.getElementById(target.id).scrollIntoView();
});
markCurrent();
