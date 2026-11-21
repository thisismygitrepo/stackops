import { h, tildify } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { createLivePanel } from "../../live_panel.js";
import { rise } from "../../motion.js";
import { toolButton } from "../../space_kit.js";
import { avatar, button, copyChip, notice } from "../../widgets.js";
import { humanize, plural, relativeTime } from "../../words.js";
import { actionBlock, areaHead, previewList, statusPill } from "./workbench_kit.js";

const TAB_PREVIEW = 4;
const SAVED_PROFILES = "/browsers-profiles/";
const WINDOW_NOTES = {
  no_endpoint: "It isn't open to agents, so its windows can't be listed.",
  unsupported_browser: "This browser can't list its windows.",
  session_in_use: "Another tool is driving it right now, so its windows can't be listed.",
};
const HOMES = { detached: "Runs in the background", tmux: "Runs in a tmux session", tuios: "Runs in a tuios pane", zellij: "Runs in a Zellij session" };
const OPEN_CLOSE = [
  { path: "agents browser launch", blurb: "Start a browser with its own profile, ready for an agent to drive." },
  { path: "agents browser batch-launch", blurb: "Start one browser for each saved profile, each at its own address." },
  { path: "agents browser close", blurb: "Stop one agent browser, or just one of its windows." },
  { path: "agents browser batch-close", blurb: "Stop every browser that was opened from a saved profile." },
];
const PROFILES = [
  { path: "agents browser replicate", blurb: "Clone a signed-in profile so several agents can browse at once." },
  { path: "agents browser declutter", blurb: "Delete caches and downloaded extras that a browser rebuilds by itself.", caution: "Deletes files" },
  { path: "agents browser install", blurb: "Install the browser tool or connector your agent needs." },
];

// The command answers in two shapes: launches StackOps tracks, or (with "All") every browser process it can find.
function describe(row) {
  if (row.launch) {
    const { launch } = row;
    return {
      browser: launch.browser, profile: `Profile ${launch.profile.replace(/^profile-/, "")}`, port: launch.port, address: `http://${launch.host === "0.0.0.0" ? "127.0.0.1" : launch.host}:${launch.port}`, tracked: true, healthy: row.state === "running",
      home: HOMES[launch.windows?.multiplexer ?? "detached"], shared: launch.relay_expected, folder: launch.profile_path, started: launch.process_created_at, windows: row.browser_windows,
    };
  }
  const port = row.browser.debugging_port;
  const folder = row.browser.profile_path ? String(row.browser.profile_path) : "";
  return {
    browser: row.browser.browser, profile: !folder ? "Your everyday profile" : folder.includes(SAVED_PROFILES) ? `Profile ${folder.split("/").at(-1)}` : "A throwaway profile", port, address: port ? `http://127.0.0.1:${port}` : null, tracked: row.launch_id !== null, healthy: true,
    home: row.runtime ? HOMES[row.runtime] : "Opened outside StackOps", shared: false, folder: row.browser.profile_path, started: row.browser.started_at, windows: row.browser_windows,
  };
}

function tabList(windows) {
  if (!Array.isArray(windows)) return h("p", { class: "wb-note", text: WINDOW_NOTES[windows?.reason] ?? "Its windows can't be listed." });
  const tabs = windows.flatMap((window) => window.tabs);
  if (tabs.length === 0) return h("p", { class: "wb-note", text: "No pages are open in it." });
  const line = (tab) => {
    const site = /^https?:/.test(tab.url) && URL.canParse(tab.url) ? new URL(tab.url).host.replace(/^www\./, "") : "";
    return h("li", { title: tab.url }, h("span", { class: "wb-page-title", text: tab.title || tab.url }), site && h("span", { class: "dim", text: site }));
  };
  return h(
    "div",
    { class: "wb-pages" },
    h("span", { class: "stat-label", text: `${plural(windows.length, "window")} · ${plural(tabs.length, "page")} open` }),
    previewList(tabs, TAB_PREVIEW, line),
  );
}

export function createBrowserArea({ tools }, { setStatus }) {
  const open = () => toolButton(tools, "agents browser launch", { label: "Open a browser", glyph: "plus", tone: "primary" });

  function card(item) {
    const close = item.tracked && item.port && button({ label: "Close", glyph: "stop", small: true, onclick: () => tools.open("agents browser close", { preset: { browser: item.browser, port: String(item.port) } }) });
    return h(
      "article",
      { class: "wb-card lit" },
      h(
        "header",
        {},
        avatar(item.browser, 44),
        h("div", {}, h("h3", { text: humanize(item.browser) }), h("span", { class: "dim", text: item.profile })),
        item.healthy ? statusPill("Running", "good", "check") : statusPill("Needs attention", "warn", "alert"),
      ),
      h("div", { class: "wb-address" }, h("span", { class: "stat-label", text: "Agents connect at" }), item.address ? copyChip(item.address) : h("span", { class: "dim", text: "Not open to agents" })),
      item.healthy ? tabList(item.windows) : h("p", { class: "wb-note", text: "It has stopped or lost part of its connection. Close it here, then open it again." }),
      h(
        "footer",
        {},
        h("span", { class: "dim", title: item.folder ? tildify(String(item.folder), state.boot.home) : undefined, text: `${item.home} · opened ${relativeTime(item.started)}${item.shared ? " · shared on your network" : ""}` }),
        close,
      ),
    );
  }

  const panel = createLivePanel({
    title: "Open right now", path: "agents browser status", extra: ["--json"], skeletonShape: "card",
    render: (data, { setCount }) => {
      const items = (Array.isArray(data) ? data : []).map(describe);
      const tracked = items.filter((item) => item.tracked).length;
      setCount(items.length === 0 ? "" : items.length === tracked ? plural(items.length, "browser") : `${plural(items.length, "browser")} · ${tracked} opened for agents`);
      setStatus(tracked ? `${tracked} open` : "None open", tracked ? "good" : "");
      if (items.length === 0) return notice({ glyph: "browser", title: "No browser is open for agents", body: "Open one and an agent can visit pages, click, fill in forms and read what is on screen.", action: open() });
      return rise(h("div", { class: "card-grid wide" }, items.map(card)));
    },
  });

  const element = h(
    "div",
    { class: "wb-area" },
    areaHead({
      title: "Browser automation", lede: "Give an agent a real browser to work in. It gets its own profile, so your everyday browsing stays separate.",
      actions: [toolButton(tools, "agents browser install", { label: "Set up browser tools", glyph: "download" }), open()],
    }),
    panel.element,
    actionBlock(tools, "Open and close", OPEN_CLOSE),
    actionBlock(tools, "Profiles and setup", PROFILES),
  );
  return { element, show: () => panel.ensure() };
}
