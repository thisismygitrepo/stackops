import { h, toast } from "/assets/scripts/dom.js";
import { request } from "/assets/scripts/state.js";
import { markStale, query, staleKeeper } from "../../data.js";
import { button } from "../../widgets.js";
import { failNotice, partHead } from "./kit.js";
import { createWifiHero } from "./wifi/hero.js";
import { askForNetwork } from "./wifi/join.js";
import { createNetworksCard } from "./wifi/networks.js";
import { API, HASHES, PATHS, go } from "./words.js";

const SETTLE_MILLISECONDS = 1500;
let page = null;
let arrival = {};

// Wi-Fi is a page: what it shows changes when a network is joined, and the page is still there to show it.
export function open(_context, { preset }) {
  if (page) page.adopt(preset ?? {});
  else arrival = preset ?? {};
  go(HASHES.wifi);
}

export function createPart(context) {
  page ??= createWifiPage(context, arrival);
  return page;
}

function createWifiPage({ tools }, preset) {
  let overview = null;
  let signal = null;
  let nearby = null;
  let address = "";
  let signalPending = false;
  let ticket = 0;
  let proposed = preset.ssid ?? "";
  const failure = h("div");
  const hero = createWifiHero();
  const networks = createNetworksCard({ onJoin: join, onLookAgain: () => load(true) });
  const body = h("div", { class: "network-stack" }, hero.element, networks.element);

  const paint = () => {
    if (overview === null) return;
    hero.paint({ overview, signal, signalPending, address });
    networks.paint(overview, nearby);
  };

  // In steps: what the system says at once, then the signal where it takes seconds, the networks in range where they may be listed, and
  // this machine's address on that adapter.
  async function load(fresh = false) {
    const mine = (ticket += 1);
    element.classList.add("loading");
    try {
      const answer = await request("GET", `${API}/wifi`);
      if (mine !== ticket) return;
      overview = answer;
      signal = answer.signal;
      signalPending = answer.signal_later;
      failure.replaceChildren();
      body.hidden = false;
    } catch (error) {
      if (mine !== ticket) return;
      keeper.spoil();
      body.hidden = overview === null;
      failure.replaceChildren(failNotice(error, () => load()));
      element.classList.remove("loading");
      return;
    }
    paint();
    const waits = [];
    if (overview.signal_later) {
      waits.push(
        request("GET", `${API}/wifi/signal`).then((answer) => answer.signal, () => null).then((found) => {
          if (mine !== ticket) return;
          signal = found;
          signalPending = false;
          paint();
        }),
      );
    }
    if (overview.nearby_blocker === "" && overview.problem === "") {
      waits.push(
        request("GET", `${API}/wifi/nearby${fresh ? "?fresh=1" : ""}`).then((answer) => answer.networks, (error) => (fresh && toast(error.message), null)).then((found) => {
          if (mine !== ticket) return;
          nearby = found;
          paint();
        }),
      );
    }
    waits.push(
      query([...PATHS.address.split(" "), "--json"]).then(({ json }) => {
        if (mine !== ticket) return;
        address = json?.interfaces?.find((item) => item.interface === overview.adapter)?.ipv4_address ?? "";
        paint();
      }, () => {}),
    );
    await Promise.all(waits);
    if (mine === ticket) element.classList.remove("loading");
  }

  async function join({ kind, name }) {
    if (overview === null || overview.connect_blocker !== "") return;
    let body = { kind, name };
    if (kind === "new") {
      const given = await askForNetwork({ name });
      if (given === null) return;
      body = { kind, ...given };
    }
    networks.setBusy(body.name);
    try {
      await request("POST", `${API}/wifi/connect`, body);
      toast(`Joined ${body.name}.`, "info");
      // The address panel and anything else that shows the connection read it again; the adapter needs a moment to get its address.
      setTimeout(markStale, SETTLE_MILLISECONDS);
    } catch (error) {
      toast(error.message);
    }
    networks.setBusy("");
    load();
  }

  const element = h(
    "div",
    { class: "network-part network-wifi", hidden: true },
    partHead({
      title: "Wi-Fi", lede: "The network this machine is on, how strong it is, and the ones it can join.",
      actions: [button({ label: "Refresh", glyph: "refresh", onclick: () => load() }), button({ label: "All options", glyph: "sliders", title: "The command's own form, with every option it has", onclick: () => tools.open(PATHS.wifi, { plain: true }) })],
    }),
    failure,
    body,
  );
  const keeper = staleKeeper(element, () => load());
  return {
    element,
    // A network named by whoever opened the tool is brought into view in the list. Nothing is joined unasked.
    show() {
      keeper.load();
      if (proposed) networks.seek(proposed);
      proposed = "";
    },
    adopt(given) {
      proposed = given.ssid ?? "";
    },
  };
}
