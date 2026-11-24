import { h, icon } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { staleKeeper } from "../../data.js";
import { emojiTile } from "../../widgets.js";
import { blurbOf, formatBytes, plural, titleOf } from "../../words.js";
import { readCloud, readDownloadPlace, readLocker, readRuns } from "./tools_api.js";

export const SCAN_CARDS = ["devops security install", "devops security export"];
export const CLOUD_CARDS = ["devops security upload", "devops security download"];
export const LOCK_CARDS = ["devops data encrypt", "devops data decrypt"];

// What this machine has for each card, as a tone and a few words. Each reads one small answer of the server; the cards show before any arrives.
// `read` holds the four answers, each asked for once however many cards use it.
const FACTS = {
  "devops security install": async (read) => {
    const { runs } = await read.runs();
    const fit = runs.find((run) => run.installable > 0);
    return fit ? ["good", `${plural(fit.installable, "app")} ready to install`] : ["", runs.length ? "No scan kept copies" : "No scans yet"];
  },
  "devops security export": async (read) => {
    const { runs } = await read.runs();
    return runs.length ? ["good", plural(runs.length, "saved scan")] : ["", "No scans yet"];
  },
  "devops security upload": async (read) => {
    const cloud = await read.cloud();
    return cloud.problem ? ["warn", "No cloud set up yet"] : ["good", `Goes to ${cloud.name}`];
  },
  "devops security download": async (read) => {
    const place = await read.place();
    return place.ready ? ["good", `${formatBytes(place.free)} free here`] : ["warn", "Not available here"];
  },
  "devops data encrypt": async (read) => {
    const locker = await read.locker();
    return locker.gpg ? ["good", `GPG ${locker.version} · ${plural(locker.keys.length, "key")}`] : ["warn", "GPG is not installed"];
  },
  "devops data decrypt": async (read) => {
    const locker = await read.locker();
    const mine = locker.keys.filter((key) => key.mine).length;
    return locker.gpg ? ["good", mine ? `${plural(mine, "private key")} here` : "Passwords only, no keys here"] : ["warn", "GPG is not installed"];
  },
};

// The Security page's cards for the tools that have a sheet of their own. Each card carries one line about this machine under its
// description, so the page says what is set up before any card is opened. `ensure` is for each time the page is shown.
export function createToolCards({ tools }) {
  const cards = new Map();
  for (const path of [...SCAN_CARDS, ...CLOUD_CARDS, ...LOCK_CARDS]) {
    const node = state.nodes.get(path);
    if (!node) continue;
    const fact = h("small", { class: "sec-card-fact" }, h("i"), h("span", { text: "Reading" }));
    const element = h(
      "button",
      { class: "tool-card lit sec-card", type: "button", onclick: () => tools.open(path) },
      emojiTile(node.icon || "✨", node.path, 40),
      h("span", { class: "tool-card-text" }, h("strong", { text: titleOf(node) }), h("span", { text: blurbOf(node) }), fact),
      icon("arrow", 14),
    );
    cards.set(path, { element, fact });
  }
  const grid = (paths) => h("div", { class: "tool-grid" }, paths.filter((path) => cards.has(path)).map((path) => cards.get(path).element));
  const grids = { scans: grid(SCAN_CARDS), cloud: grid(CLOUD_CARDS), locks: grid(LOCK_CARDS) };

  async function load() {
    const once = (ask) => {
      let asked = null;
      return () => (asked ??= ask());
    };
    const read = { runs: once(readRuns), cloud: once(readCloud), place: once(readDownloadPlace), locker: once(readLocker) };
    await Promise.all(
      [...cards].map(async ([path, { fact }]) => {
        try {
          const [tone, text] = await FACTS[path](read);
          fact.className = `sec-card-fact ${tone}`;
          fact.lastChild.textContent = text;
        } catch {
          keeper.spoil();
          fact.className = "sec-card-fact";
          fact.lastChild.textContent = "Could not be read";
        }
      }),
    );
  }
  const keeper = staleKeeper(grids.scans, load);
  return { ...grids, ensure: keeper.ensure };
}
