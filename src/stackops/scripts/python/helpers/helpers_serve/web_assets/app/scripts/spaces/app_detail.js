import { h } from "/assets/scripts/dom.js";
import { openSheet } from "../overlays.js";
import { avatar, button, keyValue, pill } from "../widgets.js";
import { plainText, relativeTime } from "../words.js";

export function openAppDetail({ app, categories, picked, onToggle, onInstall }) {
  const sheet = openSheet({ label: app.name });
  const titles = app.categories.map((label) => categories.find((category) => category.label === label)?.title ?? label);
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
      ["Last updated", app.updated_at && relativeTime(app.updated_at)],
    ]),
  );
  sheet.foot.hidden = false;
  sheet.foot.append(
    h("span", { class: "spacer" }),
    button({
      label: picked ? "Remove from selection" : "Add to selection", glyph: picked ? "close" : "plus",
      onclick: () => {
        onToggle();
        sheet.close();
      },
    }),
    button({
      label: app.installed ? "Update now" : "Install now", glyph: "download", tone: "primary",
      onclick: () => {
        sheet.close();
        onInstall();
      },
    }),
  );
}
