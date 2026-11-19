import { h, icon } from "/assets/scripts/dom.js";
import { api, on } from "/assets/scripts/state.js";
import { software } from "../data.js";
import { rise } from "../motion.js";
import { avatar, button, iconButton, notice, pill, stat } from "../widgets.js";
import { relativeTime } from "../words.js";

// One short of what a browser opens to one address at a time, so a click elsewhere is not left waiting behind the checks.
const CHECKS_AT_ONCE = 5;
// The order the list settles into once every app has an answer: what needs attention first.
const GROUPS = [["outdated", "Updates available"], ["unknown", "Could not compare"], ["current", "Up to date"]];

const groupOf = (answer) => (answer.error || answer.standing === "unknown" ? "unknown" : answer.standing === "outdated" ? "outdated" : "current");
const version = (text, tone = "") => h("span", { class: `version ${tone}`, text });

// The Updates section of Apps: every installed app that is downloaded from a GitHub repository, with the version on this machine next to the
// repository's latest release. It checks on arrival; apps installed another way are left out because GitHub cannot say what their latest version is.
export function createAppUpdates({ onUpdate }) {
  const answers = new Map();
  const rows = new Map();
  let apps = [];
  let ticket = 0;
  let loaded = false;
  let stale = false;

  const tiles = {
    all: stat({ glyph: "cube", hue: 252, label: "From GitHub" }),
    outdated: stat({ glyph: "download", hue: 30, label: "Updates available" }),
    current: stat({ glyph: "check", hue: 155, label: "Up to date" }),
    unknown: stat({ glyph: "info", hue: 200, label: "Could not compare" }),
  };
  const count = h("span", { class: "count" });
  const updateAll = button({ label: "Update all", glyph: "download", small: true, tone: "primary", onclick: () => onUpdate(apps.filter((app) => groupOf(answers.get(app.name)) === "outdated").map((app) => app.name)) });
  updateAll.hidden = true;
  const list = h("div", { class: "update-list" });
  const element = h(
    "section",
    { class: "panel updates-panel", hidden: true },
    h("header", { class: "panel-head" }, h("h2", { text: "Installed from GitHub" }), count, h("span", { class: "spacer" }), updateAll, iconButton("refresh", "Ask GitHub again", () => check(true))),
    h("div", { class: "panel-body stack" }, h("div", { class: "stats" }, Object.values(tiles).map((tile) => tile.element)), list),
  );

  function facts(answer) {
    const { installed_version: installed, latest_version: latest } = answer;
    if (latest === "") return [installed && version(installed), pill("No release published")];
    if (answer.standing === "outdated") return [version(installed), icon("arrow", 13), version(latest, "new")];
    if (answer.standing === "current") return [version(installed), pill("Up to date", "good")];
    if (answer.standing === "ahead") return [version(installed), pill(`Ahead of ${latest}`)];
    return installed ? [version(installed), version(latest), pill("Different numbering", "warn")] : [pill("Installed version unreadable", "warn"), icon("arrow", 13), version(latest)];
  }

  function row(app) {
    const answer = answers.get(app.name);
    const actions = h("div", { class: "update-actions" });
    if (answer && !answer.error) {
      actions.append(h("a", { class: "btn plain small", href: answer.release_url, target: "_blank", rel: "noopener noreferrer", title: "Opens the release on GitHub" }, icon("external", 14), h("span", { text: answer.latest_version ? "Release notes" : "Releases" })));
      if (groupOf(answer) !== "current" && answer.latest_version) actions.append(button({ label: "Update", glyph: "download", small: true, tone: "primary", onclick: () => onUpdate([app.name]) }));
    }
    const element = h(
      "li",
      { class: "session-row update-row" },
      avatar(app.name, 40),
      h("div", { class: "session-text" }, h("strong", { text: app.name }), h("a", { class: "link update-repo", href: `https://github.com/${app.repository}`, target: "_blank", rel: "noopener noreferrer", text: app.repository })),
      h("div", { class: "update-versions" }, !answer ? h("span", { class: "skeleton version-wait" }) : answer.error ? [pill("Check failed", "bad"), h("span", { class: "dim update-problem", title: answer.error, text: answer.error })] : facts(answer)),
      h("span", { class: "dim update-when", title: answer?.released_at && new Date(answer.released_at).toLocaleString(), text: answer?.released_at ? `Released ${relativeTime(answer.released_at)}` : "" }),
      actions,
    );
    rows.set(app.name, element);
    return element;
  }

  function paintSummary(done) {
    const counts = { outdated: 0, unknown: 0, current: 0 };
    for (const app of apps) if (answers.has(app.name)) counts[groupOf(answers.get(app.name))] += 1;
    const checking = done < apps.length;
    count.textContent = checking ? `Checking ${done} of ${apps.length}…` : "";
    updateAll.hidden = checking || counts.outdated < 2;
    updateAll.querySelector("span").textContent = `Update all ${counts.outdated}`;
    tiles.all.set(apps.length, "installed on this machine");
    const none = (settled) => (checking ? "none so far" : apps.length ? settled : "");
    tiles.outdated.set(counts.outdated, counts.outdated ? "a newer release is out" : none("nothing to do"));
    tiles.current.set(counts.current, counts.current ? "on the latest release" : none("none of them"));
    tiles.unknown.set(counts.unknown, counts.unknown ? "version unreadable, or no release" : none("every version was readable"));
  }

  // A design choice: while the first answers arrive the list keeps its alphabetical order, and it is sorted into groups once, at the end.
  // Sorting on every answer made the rows jump under the pointer.
  function paintList() {
    if (apps.length === 0) {
      list.replaceChildren(notice({ glyph: "cube", title: "Nothing here comes from GitHub yet", body: "Apps that are downloaded from a GitHub repository are listed here once they are installed, with the version you have and the latest one." }));
      return;
    }
    if (!apps.every((app) => answers.has(app.name))) {
      list.replaceChildren(rise(h("ul", { class: "session-list" }, apps.map(row))));
      return;
    }
    const groups = GROUPS.map(([id, title]) => [title, apps.filter((app) => groupOf(answers.get(app.name)) === id)]).filter(([, members]) => members.length > 0);
    list.replaceChildren(...groups.map(([title, members]) => h("section", { class: "update-group" }, h("h3", {}, title, h("b", { text: String(members.length) })), h("ul", { class: "session-list" }, members.map(row)))));
  }

  // `fresh` asks GitHub again; without it the server answers from what it learned in the last few minutes and only the installed versions are read
  // again, which is all that changes when an install finishes.
  async function check(fresh) {
    const mine = (ticket += 1);
    loaded = true;
    stale = false;
    element.classList.add("loading");
    try {
      apps = (await software()).apps.filter((app) => app.installed && app.repository);
    } catch (error) {
      if (mine !== ticket) return;
      element.classList.remove("loading");
      loaded = false;
      apps = [];
      paintSummary(0);
      list.replaceChildren(notice({ glyph: "alert", tone: "bad", title: "The app catalog didn't load", body: error.message, action: button({ label: "Try again", glyph: "refresh", small: true, onclick: () => check(fresh) }) }));
      return;
    }
    if (mine !== ticket) return;
    for (const name of [...answers.keys()]) if (!apps.some((app) => app.name === name)) answers.delete(name);
    const queue = [...apps];
    let done = 0;
    paintSummary(done);
    paintList();
    await Promise.all(
      Array.from({ length: CHECKS_AT_ONCE }, async () => {
        while (queue.length > 0 && mine === ticket) {
          const app = queue.shift();
          const answer = await api.softwareVersion(app.name, fresh).catch((error) => ({ error: error.message }));
          if (mine !== ticket) return;
          answers.set(app.name, answer);
          done += 1;
          rows.get(app.name).replaceWith(row(app));
          paintSummary(done);
        }
      }),
    );
    if (mine !== ticket) return;
    element.classList.remove("loading");
    paintList();
  }

  on("data-stale", () => {
    stale = true;
    if (element.isConnected && !element.closest("[hidden]")) check(false);
  });

  return { element, show: () => (!loaded || stale) && check(false) };
}
