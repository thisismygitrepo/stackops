import { h } from "/assets/scripts/dom.js";
import { request } from "/assets/scripts/state.js";
import { agentButton } from "../../agent_ask.js";
import { staleKeeper } from "../../data.js";
import { button, notice } from "../../widgets.js";
import { createForwardForm } from "./forwards/form.js";
import { createForwardList } from "./forwards/list.js";
import { failNotice, partHead } from "./kit.js";
import { API, HASHES, PATHS, go } from "./words.js";

const WATCH_MILLISECONDS = 5000;
const SETTLE_MILLISECONDS = 2500;
let page = null;
let arrival = {};

// Forward a port is a page: the form sits over the list of what is forwarding right now, and a forward started as a task stays on the
// page behind the Activity panel. What whoever opened it filled in arrives by the command's parameter names.
export function open(_context, { preset }) {
  if (page) page.adopt(preset ?? {});
  else arrival = preset ?? {};
  go(HASHES.forwards);
}

export function createPart(context) {
  page ??= createForwardsPage(context, arrival);
  return page;
}

function createForwardsPage({ activity, tools }, preset) {
  let ticket = 0;
  let hostsRead = false;
  const failure = h("div");
  const form = createForwardForm({ activity, preset, onStarted: ({ wait }) => (wait ? setTimeout(load, SETTLE_MILLISECONDS) : load()) });
  const list = createForwardList({ onStopped: () => load() });
  const body = h("div", { class: "network-stack" }, form.element, list.element);

  async function load() {
    const mine = (ticket += 1);
    element.classList.add("loading");
    try {
      const overview = await request("GET", `${API}/forwards`);
      if (mine !== ticket) return;
      failure.replaceChildren(...(overview.ssh_installed ? [] : [notice({ glyph: "plug", title: "This machine has no ssh command", body: "Forwarding goes through SSH. Install the OpenSSH client and this page starts working." })]));
      if (!overview.ssh_installed) form.disable("Forwarding needs the ssh command, which this machine does not have.");
      list.paint(overview.forwards);
    } catch (error) {
      if (mine !== ticket) return;
      keeper.spoil();
      failure.replaceChildren(failNotice(error, load));
    }
    if (mine === ticket) element.classList.remove("loading");
    // The machines are read once: the list is long and the SSH config rarely changes while the page is open.
    if (hostsRead) return;
    hostsRead = true;
    request("GET", `${API}/forwards/hosts`).then(({ hosts }) => form.setHosts(hosts), () => (hostsRead = false));
  }

  const element = h(
    "div",
    { class: "network-part network-fwd", hidden: true },
    partHead({
      title: "Forward a port", lede: "Reach a port on another machine as if it were on this one. The traffic travels inside SSH, so nothing new is opened to the network.",
      actions: [agentButton(activity, { commands: [PATHS.mapPort] }), button({ label: "Refresh", glyph: "refresh", onclick: () => load() }), button({ label: "All options", glyph: "sliders", title: "The command's own form, with every option it has", onclick: () => tools.open(PATHS.mapPort, { plain: true }) })],
    }),
    failure,
    body,
  );
  const keeper = staleKeeper(element, load);
  // A forward can start or end outside this app at any moment, so the list is read again while the page is on screen.
  setInterval(() => element.isConnected && !element.closest("[hidden]") && !document.hidden && load(), WATCH_MILLISECONDS);
  return {
    element,
    show: () => keeper.load(),
    adopt: (given) => form.adopt(given),
  };
}
