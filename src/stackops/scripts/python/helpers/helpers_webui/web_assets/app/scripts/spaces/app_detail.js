import { h, icon, tildify } from "/assets/scripts/dom.js";
import { api, state } from "/assets/scripts/state.js";
import { openSheet } from "../overlays.js";
import { avatar, button, copyChip, keyValue, pill } from "../widgets.js";
import { plainText, relativeTime } from "../words.js";
import { removeApp } from "./app_remove.js";
import { version } from "./app_updates.js";

// A moment as its day, with how long ago that was: "installed 12 Jun 2026 (5 months ago)".
const dated = (lead, value) =>
  value && h("span", { class: "dim", title: new Date(value).toLocaleString(), text: `${lead} ${new Date(value).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" })} (${relativeTime(value)})` });

export function openAppDetail({ app, categories, picked, activity, onToggle, onInstall }) {
  const sheet = openSheet({ label: app.name });
  sheet.panel.classList.add("app-sheet");
  const titles = app.categories.map((label) => categories.find((category) => category.label === label)?.title ?? label);
  // The two version rows are filled in after the sheet opens: reading a version runs the app, and the latest release is asked of GitHub.
  // Each is a line with the version and where it stands, then a line with its date.
  const installed = h("div", { class: "app-version" }, h("span", { class: "skeleton version-wait" }));
  const latest = h("div", { class: "app-version" }, h("span", { class: "skeleton version-wait" }));
  const line = (...parts) => h("div", {}, parts.filter(Boolean));
  const primary = button({
    label: app.installed ? "Update now" : "Install now", glyph: "download", tone: "primary",
    onclick: () => {
      sheet.close();
      onInstall();
    },
  });
  sheet.body.append(
    h(
      "header",
      { class: "app-detail-head" },
      avatar(app.name, 72),
      h("div", {}, h("h1", { text: app.name }), h("p", { text: plainText(app.summary) }), h("div", { class: "app-detail-pills" }, app.installed && pill("Installed on this machine", "good"), app.mine && pill("From my catalog", "accent"))),
    ),
    keyValue([
      ["Category", titles.join(", ")],
      ["License", app.license],
      ["Website", app.homepage && h("a", { class: "link", href: app.homepage, target: "_blank", rel: "noopener noreferrer", text: app.homepage.replace(/^https?:\/\/(www\.)?/, "") })],
      ["Last commit", app.updated_at && relativeTime(app.updated_at)],
      ["Installed version", app.installed ? installed : null],
      ["Latest release", app.repository && latest],
      ["Location", app.binary && copyChip(app.binary, tildify(app.binary, state.boot.home))],
    ]),
  );
  if (app.installed || app.repository) {
    api.softwareVersion(app.name, false).then(
      (answer) => {
        const { installed_version: mine, latest_version: theirs, standing } = answer;
        const behind = app.installed && standing === "outdated";
        // Once the versions are known the main button says what it does: bring in the newer release, or put the same one in again.
        if (behind) primary.querySelector("span").textContent = `Update to ${theirs}`;
        else if (app.installed && theirs && standing === "current") primary.querySelector("span").textContent = "Reinstall";
        installed.replaceChildren(
          line(mine ? version(mine) : pill("The app does not say", "warn"), theirs && standing === "current" && pill("Up to date", "good"), theirs && standing === "ahead" && pill("Ahead of the latest release")),
          line(dated("installed", app.installed_at)),
        );
        latest.replaceChildren(
          line(theirs ? version(theirs, behind ? "new" : "") : pill("No release published"), behind && pill("Update available", "accent")),
          line(
            dated("released", answer.released_at),
            h("a", { class: "link", href: answer.release_url, target: "_blank", rel: "noopener noreferrer", title: "Opens the release on GitHub" }, theirs ? "Release notes" : "Releases", icon("external", 12)),
          ),
        );
      },
      (error) => {
        installed.replaceChildren(line(pill("Check failed", "bad")), line(dated("installed", app.installed_at)));
        latest.replaceChildren(line(pill("Check failed", "bad")), line(h("span", { class: "dim", text: error.message })));
      },
    );
  }
  const remove = button({ label: "Delete", glyph: "trash", tone: "ghost", title: "Deletes this app from this machine", onclick: async () => (await removeApp(app, activity)) && sheet.close() });
  remove.classList.add("app-delete");
  sheet.foot.hidden = false;
  sheet.foot.append(
    ...[
      app.installed && remove,
      h("span", { class: "spacer" }),
      button({
        label: picked ? "Remove from selection" : "Add to selection", glyph: picked ? "close" : "plus",
        onclick: () => {
          onToggle();
          sheet.close();
        },
      }),
      primary,
    ].filter(Boolean),
  );
}
