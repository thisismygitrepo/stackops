import { h } from "/assets/scripts/dom.js";
import { createLivePanel } from "../../live_panel.js";
import { rise } from "../../motion.js";
import { toolButton } from "../../space_kit.js";
import { avatar, button, copyChip, keyValue, notice, pill } from "../../widgets.js";
import { humanize, plural, relativeTime } from "../../words.js";
import { cardHead, pathText, savedProfileName, statusPill } from "./workbench_kit.js";

const HOST_PREVIEW = 3;
// The sites the command checks in every profile without being asked, by the names it reports them under.
const SERVICES = { google: "Google", microsoft: "Microsoft", github: "GitHub", slack: "Slack" };
const SIGN_INS = { "signed-in": ["Signed in", "good", "check"], likely: ["Probably signed in", "warn", null], none: ["Not signed in", "", null] };

function siteSignIn(signIn) {
  const extra = signIn.hosts.length - HOST_PREVIEW;
  return h(
    "div",
    { class: "wb-signin" },
    h("div", { class: "wb-line-actions" }, statusPill(...SIGN_INS[signIn.state]), signIn.last_active && h("span", { class: "dim", text: `used ${relativeTime(signIn.last_active)}` })),
    signIn.accounts.map((account) => h("span", { text: account })),
    signIn.saved_usernames.length > 0 && h("span", { text: `Saved login: ${signIn.saved_usernames.join(", ")}` }),
    signIn.hosts.length > 0 &&
      h("span", { class: "dim", title: `Cookies: ${signIn.cookie_names.join(", ")}`, text: `Found on ${signIn.hosts.slice(0, HOST_PREVIEW).join(", ")}${extra > 0 ? ` and ${extra} more` : ""}` }),
  );
}

export function createProfilesPanel({ tools }) {
  function card(row) {
    const folder = String(row.user_data_path);
    const address = row.debugging_port && `http://127.0.0.1:${row.debugging_port}`;
    // Only a saved profile can be opened by name; the browser's own profiles are listed to be looked at or copied.
    const saved = savedProfileName(folder);
    const open = saved && !row.running && button({ label: "Open", glyph: "plus", small: true, onclick: () => tools.open("agents browser launch", { preset: { browser: row.browser, profile: saved } }) });
    return h(
      "article",
      { class: "wb-card lit" },
      cardHead(avatar(row.profile, 44), row.profile, `${humanize(row.browser)} · ${row.last_used ? `used ${relativeTime(row.last_used)}` : "never opened"}`, row.running ? statusPill("Running", "good", "check") : statusPill("Closed", "", null)),
      keyValue([
        ["Browser account", row.browser_account ?? h("span", { class: "dim", text: "Not signed in" })],
        [
          "Signed in to",
          row.signed_in_services.length > 0
            ? h("div", { class: "chip-row" }, row.signed_in_services.map((service) => pill(SERVICES[service] ?? humanize(service), "good")))
            : h("span", { class: "dim", text: `None of ${Object.values(SERVICES).slice(0, -1).join(", ")} or ${Object.values(SERVICES).at(-1)}` }),
        ],
        ...row.sites.map((signIn) => [SERVICES[signIn.site.toLowerCase()] ?? signIn.site, siteSignIn(signIn)]),
      ]),
      h("footer", {}, pathText(folder), address ? copyChip(address) : open),
    );
  }

  return createLivePanel({
    title: "Profiles and sign-ins", path: "agents browser profiles", extra: ["--json"], skeletonShape: "card",
    render: (data, { setCount }) => {
      const rows = Array.isArray(data) ? data : [];
      const running = rows.filter((row) => row.running).length;
      setCount(rows.length === 0 ? "" : `${plural(rows.length, "profile")}${running ? ` · ${running} running` : ""}`);
      if (rows.length === 0) {
        return notice({
          glyph: "browser", title: "No saved profiles yet",
          body: "A saved profile keeps its sign-ins between runs. Copy one from your everyday browser and agents can use the accounts you are signed in to.",
          // Started with nothing filled in, the copy command only prints how to use it. With "native" set it lists the everyday browser's profiles to pick from.
          action: toolButton(tools, "agents browser replicate", { label: "Copy a profile", glyph: "copy", preset: { native: "on" } }),
        });
      }
      return h(
        "div",
        { class: "stack" },
        rise(h("div", { class: "card-grid wide" }, rows.map(card))),
        h("p", { class: "wb-note", text: "Each sign-in is read from the cookies a profile holds, and a site can end a session before its cookie expires. To check another site, open Options and type its name under Sites." }),
      );
    },
  });
}
