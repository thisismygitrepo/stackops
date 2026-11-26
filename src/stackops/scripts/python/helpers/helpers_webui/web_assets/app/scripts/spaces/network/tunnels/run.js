import { h, icon } from "/assets/scripts/dom.js";
import { openDialog } from "../../../overlays.js";
import { button, copyChip } from "../../../widgets.js";
import { choiceCards, reason } from "../kit.js";
import { titleOf } from "./model.js";

const WAYS = [
  ["task", "In a task here (the default)", "The tunnel runs in the Activity panel, where you can watch what it says. It is up for as long as that task runs: stopping the task or closing StackOps takes it down."],
  ["background", "As a background service", "The system takes the tunnel over, keeps it running after StackOps is closed and starts it again if it fails. It asks for your password, and a restart of the machine ends it."],
];

// Asks how to run a tunnel and says what running it puts on the internet, before anything starts. Resolves to the way picked, or null.
export function askHowToRun({ tunnel, local, ask }) {
  const dialog = openDialog({ label: `Run ${titleOf(tunnel)}` });
  let way = "task";
  const named = tunnel.routes.filter((route) => route.hostname);
  const ways = choiceCards(WAYS, { value: way, blocked: { background: local.background_blocker }, onPick: (id) => (way = id) });
  dialog.body.classList.add("network-tun-run");
  dialog.body.append(
    h("h2", { text: `Run ${titleOf(tunnel)} on this machine` }),
    named.length > 0
      ? h(
          "div",
          { class: "network-tun-routes" },
          h("p", { text: `While it runs, anyone on the internet who opens ${named.length === 1 ? "this address reaches the service" : "one of these addresses reaches a service"} on this machine:` }),
          h("ul", {}, named.map((route) => h("li", {}, copyChip(`https://${route.hostname}${route.path}`, `${route.hostname}${route.path}`), icon("arrow", 14), h("code", { text: route.service })))),
        )
      : h("p", { text: "This machine's configuration names no addresses for this tunnel, so what it publishes is whatever its configuration on Cloudflare says." }),
    !tunnel.hasCredentials && reason("No credentials file for this tunnel was found in ~/.cloudflared. Unless the configuration points to one somewhere else, it will not start."),
    (tunnel.running.length > 0 || tunnel.asService) && reason("A copy of this tunnel already runs on this machine. A second one works, and adds four more connections from the same place."),
    ways.element,
    h("div", { class: "dialog-actions" }, ask, button({ label: "Cancel", onclick: () => dialog.close(null) }), button({ label: "Run the tunnel", glyph: "play", tone: "primary", onclick: () => dialog.close(way) })),
  );
  return dialog.closed.then((answer) => answer ?? null);
}
