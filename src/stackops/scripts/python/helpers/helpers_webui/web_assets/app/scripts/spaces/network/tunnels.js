import { h, icon, toast } from "/assets/scripts/dom.js";
import { request } from "/assets/scripts/state.js";
import { agentButton } from "../../agent_ask.js";
import { query, staleKeeper } from "../../data.js";
import { button, copyChip, notice, pill, searchInput, skeleton } from "../../widgets.js";
import { plural } from "../../words.js";
import { failNotice, fill, partHead, reason } from "./kit.js";
import { tunnelCard } from "./tunnels/card.js";
import { handleOf, isConnected, isHere, mergeTunnels, titleOf } from "./tunnels/model.js";
import { askHowToRun } from "./tunnels/run.js";
import { API, HASHES, PATHS, go } from "./words.js";

const SETTLE_MILLISECONDS = 4000;
const FILTERS = [["all", "All", () => true], ["connected", "Connected", isConnected], ["idle", "Not connected", (tunnel) => !isConnected(tunnel)], ["here", "On this machine", isHere]];
const FILTER_FROM = 4;
let page = null;
let arrival = {};

// Cloudflare tunnels are one page for two commands, `tunnel-status` and `run-tunnel`: running a tunnel is a pick from the tunnels the
// status shows, and the status is where a tunnel that was just started turns up. A tunnel named by whoever opened it is brought into view.
export function open(_context, { preset }) {
  if (page) page.adopt(preset ?? {});
  else arrival = preset ?? {};
  go(HASHES.tunnels);
}

export function createPart(context) {
  page ??= createTunnelsPage(context, arrival);
  return page;
}

function createTunnelsPage({ activity, tools }, preset) {
  let local = null;
  let account = null;
  let accountProblem = "";
  let accountPending = false;
  let filter = "all";
  let term = (preset.tunnel_name ?? "").toLowerCase();
  let ticket = 0;
  const health = new Map();
  const failure = h("div");
  const facts = h("div", { class: "network-facts network-tun-facts" });
  const notes = h("div", { class: "network-notes" });
  const count = h("span", { class: "count" });
  const chips = h("div", { class: "chip-row" });
  const search = searchInput({
    placeholder: "Filter by name or address",
    oninput: (value) => {
      term = value.trim().toLowerCase();
      paintCards();
    },
  });
  search.input.value = preset.tunnel_name ?? "";
  const toolbar = h("div", { class: "network-toolbar", hidden: true }, chips, h("span", { class: "spacer" }), count, search.element);
  const grid = h("div", { class: "network-tun-grid" }, skeleton(2, "card"));
  const body = h("div", { class: "network-stack" }, facts, notes, toolbar, grid);
  let tunnels = [];

  const fact = (label, value) => h("div", { class: "network-fact" }, h("span", { text: label }), h("strong", {}, value));

  function paintCards() {
    const accepts = FILTERS.find(([id]) => id === filter)[2];
    const found = tunnels.filter((tunnel) => accepts(tunnel) && `${tunnel.name} ${tunnel.id} ${tunnel.routes.map((route) => `${route.hostname} ${route.service}`).join(" ")}`.toLowerCase().includes(term));
    count.textContent = found.length === tunnels.length ? plural(tunnels.length, "tunnel") : `${found.length} of ${plural(tunnels.length, "tunnel")}`;
    if (tunnels.length === 0) {
      grid.replaceChildren(
        accountPending
          ? h("div", { class: "network-tun-wide" }, skeleton(2, "card"))
          : notice({
              glyph: "share", title: "No tunnel yet",
              body: local.signed_in ? "The Cloudflare account this machine is signed in to has no tunnel, and no configuration here names one." : "This machine holds no tunnel configuration or credentials, and it is not signed in to Cloudflare, so the tunnels on the account cannot be listed.",
            }),
      );
      return;
    }
    grid.replaceChildren(...(found.length ? found.map((tunnel) => tunnelCard({ tunnel, health: health.get(handleOf(tunnel)), listKnown: account !== null, canAsk: local.signed_in, onRun: run, onHealth: checkHealth })) : [notice({ glyph: "search", title: "No tunnel matches", body: "Try another word, or show all of them." })]));
  }

  function paint() {
    if (local === null) return;
    body.hidden = !local.installed;
    if (!local.installed) {
      failure.replaceChildren(
        notice({
          glyph: "share", title: "cloudflared is not installed",
          body: "Cloudflare tunnels are run by a small program called cloudflared. Install it and this page shows the tunnels on your account, where each one is connected, and a way to run one here.",
          action: h("a", { class: "btn primary", href: "#/apps/cloudflared" }, icon("download", 16), h("span", { text: "Install cloudflared" })),
        }),
      );
      return;
    }
    tunnels = mergeTunnels(local, account);
    fill(
      facts,
      fact("cloudflared", local.version || "installed"),
      fact("Cloudflare account", local.signed_in ? pill("Signed in", "good") : pill("Not signed in", "warn")),
      local.service_known && fact("Installed service", local.service_active ? pill("Running", "good") : pill("Not running", "")),
      local.background_active && fact("Background tunnel", pill("Running", "accent")),
      fact("Running here now", local.running.length === 0 ? "None" : local.running.length === 1 ? "1 copy" : `${local.running.length} copies`),
    );
    notes.replaceChildren(
      ...[
        !local.signed_in && h("p", { class: "network-reason" }, icon("info", 14), h("span", { text: "The list of tunnels on your account needs this machine to be signed in to Cloudflare. In a terminal:" }), copyChip("cloudflared tunnel login")),
        accountProblem && local.signed_in && reason(`Cloudflare's list of tunnels did not arrive: ${accountProblem}`),
        local.background_active && h("p", { class: "network-reason" }, icon("info", 14), h("span", { text: "A background tunnel is running as a system service. To stop it, in a terminal:" }), copyChip("sudo systemctl stop cloudflared-tunnel")),
        ...[local.config, local.service_config].filter((config) => config.problem).map((config) => reason(`${config.path}: ${config.problem}`)),
      ].filter(Boolean),
    );
    toolbar.hidden = tunnels.length < FILTER_FROM && term === "";
    chips.replaceChildren(
      ...FILTERS.map(([id, label, accepts]) =>
        h(
          "button",
          {
            class: "chip-button", type: "button", "aria-pressed": String(id === filter),
            onclick: () => {
              filter = id;
              paint();
            },
          },
          h("span", { text: label }),
          h("b", { text: String(tunnels.filter(accepts).length) }),
        ),
      ),
    );
    paintCards();
  }

  // In steps: what this machine holds, at once; then Cloudflare's list of the account's tunnels, which needs the network.
  async function load() {
    const mine = (ticket += 1);
    element.classList.add("loading");
    try {
      const answer = await request("GET", `${API}/tunnels`);
      if (mine !== ticket) return;
      local = answer;
      failure.replaceChildren();
    } catch (error) {
      if (mine !== ticket) return;
      keeper.spoil();
      body.hidden = local === null;
      failure.replaceChildren(failNotice(error, load));
      element.classList.remove("loading");
      return;
    }
    accountPending = local.installed && local.signed_in;
    paint();
    if (accountPending) {
      try {
        const answer = await request("GET", `${API}/tunnels/account`);
        if (mine !== ticket) return;
        account = answer.tunnels;
        accountProblem = "";
      } catch (error) {
        if (mine !== ticket) return;
        accountProblem = error.message;
      }
      accountPending = false;
      paint();
    }
    element.classList.remove("loading");
  }

  // One tunnel's health through the CLI's own status command, asked for when its card is pressed: each asks Cloudflare and runs checks here.
  async function checkHealth(tunnel) {
    const handle = handleOf(tunnel);
    health.set(handle, null);
    paintCards();
    const config = local.service_config.exists ? local.service_config : local.config;
    const hostnames = tunnel.routes.filter((route) => route.hostname && !route.hostname.includes("*")).map((route) => route.hostname);
    const check = [...PATHS.tunnelStatus.split(" "), "--json", "--cloudflared", local.binary, ...(local.service_known && config.exists ? ["--config", config.path, ...hostnames.flatMap((hostname) => ["--hostname", hostname])] : ["--no-local"]), "--", handle];
    try {
      health.set(handle, (await query(check, true)).json ?? { error: "The command gave no answer to read." });
    } catch (error) {
      health.set(handle, { error: error.message });
    }
    paintCards();
  }

  async function run(tunnel) {
    const way = await askHowToRun({ tunnel, local });
    if (way === null) return;
    try {
      // `--yes` because the question was just asked here. Interactive, so a background start can ask for the password in the console.
      await activity.start({ title: `Run tunnel ${titleOf(tunnel)}`, emoji: "🚀", arguments: [...PATHS.runTunnel.split(" "), "--yes", "--tunnel-name", handleOf(tunnel), ...(way === "background" ? ["--background"] : [])], interactive: true, reveal: true });
      // The tunnel needs a moment to reach Cloudflare before the list shows its connections.
      setTimeout(load, SETTLE_MILLISECONDS);
    } catch (error) {
      toast(error.message);
    }
  }

  const element = h(
    "div",
    { class: "network-part network-tun", hidden: true },
    partHead({
      title: "Cloudflare tunnels", lede: "A tunnel publishes something that runs on this machine under a public address, without opening a port. Here is which tunnels exist, where each is connected, what it publishes, and a way to run one.",
      actions: [
        agentButton(activity, { title: "Cloudflare tunnels", commands: [PATHS.tunnelStatus, PATHS.runTunnel] }),
        button({ label: "Refresh", glyph: "refresh", onclick: () => load() }),
        button({ label: "Status options", glyph: "sliders", title: "The status command's own form, which can also check other machines over SSH", onclick: () => tools.open(PATHS.tunnelStatus, { plain: true }) }),
        button({ label: "Run options", glyph: "sliders", title: "The run command's own form", onclick: () => tools.open(PATHS.runTunnel, { plain: true }) }),
      ],
    }),
    failure,
    body,
  );
  const keeper = staleKeeper(element, load);
  return {
    element,
    show: () => keeper.load(),
    adopt(given) {
      term = (given.tunnel_name ?? "").toLowerCase();
      search.input.value = given.tunnel_name ?? "";
      paint();
    },
  };
}
