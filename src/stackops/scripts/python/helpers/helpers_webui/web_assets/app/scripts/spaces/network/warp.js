import { h, icon, toast } from "/assets/scripts/dom.js";
import { request, state } from "/assets/scripts/state.js";
import { query, staleKeeper } from "../../data.js";
import { confirmAction } from "../../overlays.js";
import { button, copyChip, skeleton } from "../../widgets.js";
import { card, cardHead, failNotice, fill, mark, partHead, reason } from "./kit.js";
import { API, HASHES, PATHS, go } from "./words.js";

const RECHECK_MILLISECONDS = 2500;
const RECHECK_LIMIT = 12;
const WARP_SITE = "https://one.one.one.one/";
let page = null;

// What each state `warp-cli` reports means for someone who has never run it, and what the button does from there.
const STANDINGS = {
  connected: () => ({ tone: "good", glyph: "shield", title: "WARP is on", body: "This machine's traffic goes through Cloudflare, and the internet sees Cloudflare's address in place of your own.", action: "" }),
  connecting: () => ({ tone: "warn", glyph: "sync", title: "WARP is connecting", body: "It is on its way. This page looks again every few seconds.", action: "" }),
  disconnected: () => ({ tone: "", glyph: "power", title: "WARP is off", body: "This machine reaches the internet directly, under its own address.", action: "Connect" }),
  registration_missing: () => ({ tone: "warn", glyph: "info", title: "This machine is not registered with WARP yet", body: "Connecting registers it with Cloudflare first. That happens once and takes a few seconds.", action: "Register and connect" }),
  daemon_down: ({ system }) => ({ tone: "bad", glyph: "alert", title: "The WARP service is not running", body: system === "Linux" ? "Connecting starts the service first, which asks for your password." : "Open the Cloudflare WARP app once so that its service starts. After that this button can connect it.", action: "Connect" }),
  unable: () => ({ tone: "bad", glyph: "alert", title: "WARP cannot connect right now", body: "WARP gave this reason:", action: "Try to connect" }),
  unreadable: () => ({ tone: "bad", glyph: "alert", title: "WARP did not answer", body: "Its command is installed but its status could not be read:", action: "Try to connect" }),
  not_installed: ({ installable, system }) => ({
    tone: "", glyph: "download", title: "WARP is not installed on this machine",
    body: installable
      ? `Connecting installs it first, ${system === "macOS" ? "with Homebrew" : "from Cloudflare's own package repository"}, and then connects. WARP is Cloudflare's free VPN-like client: it sends this machine's traffic through Cloudflare.`
      : `StackOps has no way to install WARP on ${system}. Install it from Cloudflare, then come back to this page.`,
    action: installable ? "Install and connect" : "",
  }),
};

const sameAddress = (left, right) => left?.ip === right?.ip;

// Connect WARP is a page: the point of it is the address before and after, and the after is only known once the run has ended.
export function open() {
  go(HASHES.warp);
}

export function createPart(context) {
  page ??= createWarpPage(context);
  return page;
}

function createWarpPage({ activity, tools }) {
  let overview = null;
  // The address the internet sees: undefined while it is being looked up, null when the lookup failed, with `addressProblem` as the reason.
  let address = undefined;
  let addressProblem = "";
  let run = null;
  let update = false;
  let starting = false;
  let ticket = 0;
  let rechecks = 0;
  const failure = h("div");
  const hero = h("section", { class: "network-hero" }, skeleton(1, "card"));
  const addresses = h("div", { class: "network-warp-addresses" }, skeleton(1, "card"));
  const outcome = h("div");
  const updateToggle = h("button", { class: "toggle-row", type: "button", role: "switch", "aria-checked": "false", onclick: () => setUpdate(!update) }, h("span", {}, h("strong", { text: "Update WARP first" }), h("span", { class: "field-hint", text: " Fetches the newest WARP before connecting. Default: off." })), h("i", { class: "switch" }));

  function setUpdate(next) {
    update = next;
    updateToggle.setAttribute("aria-checked", String(update));
  }

  const addressCard = (label, info, standing) =>
    card(
      { class: "network-warp-address" },
      h("span", { class: "overline", text: label }),
      info ? copyChip(info.ip) : h("strong", { class: "dim", text: info === undefined ? "Looking it up…" : "Unavailable" }),
      info === null && label !== "Before" && h("span", { class: "dim", text: addressProblem ? `The lookup failed: ${addressProblem}` : "The lookup of this machine's public address did not answer." }),
      info && h("span", { text: [info.city, info.country_name].filter(Boolean).join(", ") || "Place unknown" }),
      info && h("span", { class: "dim", text: info.org || "Network unknown" }),
      standing && h("span", { class: "dim", text: standing }),
    );

  function paint() {
    if (overview === null) return;
    const words = STANDINGS[overview.standing](overview);
    const busy = starting || run?.phase === "running";
    fill(
      hero,
      h(
        "div",
        { class: `network-hero-top ${words.tone}` },
        mark(words.tone, words.glyph),
        h("div", { class: "network-hero-text" }, h("h2", { text: words.title }), h("p", { text: words.body }), ["unable", "unreadable"].includes(overview.standing) && overview.detail && h("p", { class: "network-hero-hint", text: overview.detail })),
        h(
          "div",
          { class: "network-hero-actions" },
          words.action && button({ label: busy ? "Connecting…" : words.action, glyph: overview.standing === "not_installed" ? "download" : "power", tone: "primary", onclick: connect }),
          overview.standing === "connected" && button({ label: "Get another address", glyph: "sync", title: "Opens the tool that makes WARP reconnect until the address changes", onclick: () => tools.open(PATHS.switchAddress) }),
          overview.standing === "not_installed" && !overview.installable && h("a", { class: "btn", href: WARP_SITE, target: "_blank", rel: "noopener noreferrer" }, icon("external", 16), h("span", { text: "Cloudflare's WARP page" })),
        ),
      ),
      words.action && reason("Connections that are open right now, such as SSH sessions and a company VPN, can drop when the route changes."),
      overview.standing === "connected" && h("p", { class: "network-reason" }, icon("info", 14), h("span", { text: "StackOps has no command that switches WARP off. In a terminal:" }), copyChip("warp-cli disconnect")),
    );
    for (const control of hero.querySelectorAll(".btn.primary")) control.disabled = busy;
    addresses.replaceChildren(
      ...(run?.phase === "done"
        ? [addressCard("Before", run.before, run.beforeStanding), h("span", { class: "network-warp-arrow" }, icon("arrow", 22)), addressCard("Now", address, STANDINGS[overview.standing](overview).title)]
        : [addressCard("How the internet sees this machine right now", address, "")]),
    );
    outcome.replaceChildren(
      ...(run?.phase === "done"
        ? [
            h(
              "p",
              { class: `network-warp-outcome ${run.exitCode === 0 ? "good" : "bad"}` },
              icon(run.exitCode === 0 ? "check" : "alert", 16),
              h("span", {
                text:
                  run.exitCode !== 0
                    ? "WARP did not connect. The Activity panel has what the command said."
                    : address && run.before && !sameAddress(run.before, address)
                      ? `Connected. The internet now sees ${address.ip} where it saw ${run.before.ip}.`
                      : "Connected. The address the internet sees is the same as before, which is what happens when WARP was already on.",
              }),
              button({ label: "Show the run", small: true, tone: "ghost", onclick: () => activity.reveal(run.id) }),
            ),
          ]
        : []),
    );
  }

  async function load(fresh = false) {
    const mine = (ticket += 1);
    element.classList.add("loading");
    // The address is a question to the network and can take a moment, so the state is shown without waiting for it.
    const looked = query([...PATHS.address.split(" "), "--json"], fresh).then(({ json }) => json, () => null).then((found) => {
      if (mine !== ticket) return;
      address = found?.public ?? null;
      addressProblem = found?.public_error ?? "";
      paint();
    });
    try {
      const answer = await request("GET", `${API}/warp`);
      if (mine !== ticket) return;
      overview = answer;
      failure.replaceChildren();
      body.hidden = false;
      paint();
    } catch (error) {
      if (mine !== ticket) return;
      keeper.spoil();
      body.hidden = overview === null;
      failure.replaceChildren(failNotice(error, () => load(true)));
    }
    await looked;
    if (mine !== ticket) return;
    element.classList.remove("loading");
    // A connection on its way is watched until it settles, for half a minute at most.
    if (overview?.standing === "connecting" && rechecks < RECHECK_LIMIT && !element.closest("[hidden]")) {
      rechecks += 1;
      setTimeout(() => mine === ticket && load(true), RECHECK_MILLISECONDS);
    } else if (overview?.standing !== "connecting") rechecks = 0;
  }

  async function connect() {
    if (starting || run?.phase === "running" || overview === null) return;
    if (overview.standing === "not_installed" && !(await confirmAction({ title: "Install WARP and connect?", body: `This installs Cloudflare WARP on this machine${state.boot.platform === "macOS" ? " with Homebrew" : ", which asks for your password"}, registers it with Cloudflare and connects it. From then on this machine's traffic goes through Cloudflare until WARP is switched off.`, confirm: "Install and connect" }))) return;
    starting = true;
    paint();
    try {
      // Interactive: starting the service on Linux asks for a password in the console.
      const task = await activity.start({ title: "Connect WARP", emoji: "🔌", arguments: [...PATHS.warp.split(" "), ...(update ? ["--update"] : [])], interactive: true, reveal: true });
      run = { phase: "running", id: task.id, before: address ?? null, beforeStanding: STANDINGS[overview.standing](overview).title };
      starting = false;
      paint();
      const ended = await task.done;
      run = { ...run, phase: "done", exitCode: ended.exit_code };
      address = undefined;
      await load(true);
    } catch (error) {
      toast(error.message);
    } finally {
      starting = false;
      paint();
    }
  }

  const body = h("div", { class: "network-stack" }, hero, outcome, addresses, card({ class: "network-warp-options" }, cardHead("Before it connects"), updateToggle));
  const element = h(
    "div",
    { class: "network-part network-warp", hidden: true },
    partHead({
      title: "Cloudflare WARP", lede: "WARP sends this machine's traffic through Cloudflare, which changes the address the internet sees. Here is whether it is on, and one button to connect it.",
      actions: [button({ label: "Check again", glyph: "refresh", onclick: () => load(true) }), button({ label: "All options", glyph: "sliders", title: "The command's own form, with every option it has", onclick: () => tools.open(PATHS.warp, { plain: true }) })],
    }),
    failure,
    body,
  );
  // The refresh signal that follows the run is sat out: the run's own ending reads everything again, once.
  const keeper = staleKeeper(element, () => load(), false);
  return { element, show: () => keeper.load() };
}
