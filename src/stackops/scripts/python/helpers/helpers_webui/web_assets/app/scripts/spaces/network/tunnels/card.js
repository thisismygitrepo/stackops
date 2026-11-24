import { h, icon } from "/assets/scripts/dom.js";
import { button, copyChip, pill } from "../../../widgets.js";
import { plural, relativeTime } from "../../../words.js";
import { isConnected, placesOf, redundancyOf, titleOf } from "./model.js";

const PER_COPY = 4;
const ROUTES_SHOWN = 6;

// A tunnel's connections as a picture: this side, the wire, and one dot per connection gathered under the data centre it reaches.
function picture(tunnel) {
  const places = placesOf(tunnel);
  const unknown = tunnel.connections === null;
  return h(
    "div",
    { class: `network-tun-picture${isConnected(tunnel) ? " live" : ""}` },
    h("div", { class: "network-tun-end" }, icon("server", 18), h("span", { text: tunnel.running.length > 0 || tunnel.asService ? "Running here" : "Its machines" })),
    h("i", { class: "network-tun-wire" }),
    h(
      "div",
      { class: "network-tun-places" },
      places.length > 0
        ? places.map(([place, count]) => h("div", { class: "network-tun-place", title: `${plural(count, "connection")} to Cloudflare's ${place} data centre` }, h("span", { class: "network-tun-dots" }, Array.from({ length: count }, () => h("b"))), h("code", { text: place })))
        : h("div", { class: "network-tun-place empty" }, h("span", { class: "network-tun-dots" }, Array.from({ length: PER_COPY }, () => h("b"))), h("code", { text: unknown ? "not asked" : "none" })),
    ),
    h("i", { class: "network-tun-wire" }),
    h("div", { class: "network-tun-end" }, icon("globe", 18), h("span", { text: "Cloudflare" })),
  );
}

function healthBlock(health) {
  if (health === undefined) return null;
  if (health === null) return h("p", { class: "dim", text: "Reading its health…" });
  if (health.error) return h("p", { class: "network-key-bad", text: `Its health could not be read: ${health.error}` });
  const { health: totals, connectors } = health;
  const expected = totals.connector_count * PER_COPY;
  const verdict = redundancyOf(totals);
  return h(
    "div",
    { class: "network-tun-health" },
    h("p", { class: `network-tun-verdict ${verdict.tone}`, text: verdict.text }),
    expected > 0 &&
      h(
        "div",
        { class: "network-tun-sessions", title: "Each running copy keeps four connections open" },
        h("span", { class: "network-tun-bar" }, h("i", { style: `--share:${Math.min(totals.edge_session_count / expected, 1)}` })),
        h("span", { text: `${totals.edge_session_count} of ${expected} connections open` }),
      ),
    totals.versions.length > 0 &&
      h("div", { class: "network-key-facts" }, h("span", { class: "dim", text: "Versions running:" }), totals.versions.map(([version, count]) => pill(`${version} × ${count}`, totals.versions.length > 1 ? "warn" : "")), totals.versions.length > 1 && h("span", { class: "dim", text: "The copies run different versions." })),
    connectors.map((connector) =>
      h(
        "div",
        { class: "network-key-facts" },
        h("span", { class: "dim", text: connector.host === "local" ? "On this machine:" : `On ${connector.host}:` }),
        pill(connector.service_active ? "Service running" : "Service not running", connector.service_active ? "good" : "warn"),
        pill(`cloudflared ${connector.version}`, ""),
        pill(connector.config_valid ? "Configuration valid" : "Configuration not valid", connector.config_valid ? "good" : "bad"),
        connector.route_coverage.filter(([, covered]) => !covered).map(([hostname]) => pill(`${hostname} has no route here`, "bad")),
      ),
    ),
  );
}

function routesBlock(tunnel) {
  if (tunnel.routes.length === 0) return h("p", { class: "dim", text: tunnel.hasCredentials || tunnel.configured ? "This machine's configuration names no routes for it." : "What it publishes is set on the machines that run it, and this is not one of them." });
  const named = tunnel.routes.filter((route) => route.hostname);
  const rest = tunnel.routes.find((route) => !route.hostname);
  const row = (route) => h("li", {}, copyChip(`https://${route.hostname}${route.path}`, `${route.hostname}${route.path}`), icon("arrow", 14), h("code", { text: route.service }));
  return h(
    "div",
    { class: "network-tun-routes" },
    h("span", { class: "overline", text: `Publishes ${named.length} address${named.length === 1 ? "" : "es"} from this machine` }),
    h("ul", {}, named.slice(0, ROUTES_SHOWN).map(row)),
    named.length > ROUTES_SHOWN && h("details", { class: "fold" }, h("summary", {}, icon("chevron", 13), h("span", { text: `${named.length - ROUTES_SHOWN} more` })), h("ul", {}, named.slice(ROUTES_SHOWN).map(row))),
    rest && h("span", { class: "dim", text: `Anything else is answered with ${rest.service.replace("http_status:", "the status ")}.` }),
  );
}

// One tunnel: what it is called, whether it is connected and from where, how healthy it is, what it publishes, and the way to run it.
// `listKnown` is whether Cloudflare's list of the account's tunnels arrived, and `canAsk` whether this machine is signed in to ask about one.
export function tunnelCard({ tunnel, health, listKnown, canAsk, onRun, onHealth }) {
  const connected = isConnected(tunnel);
  const count = tunnel.connections?.length ?? 0;
  return h(
    "article",
    { class: "network-tun-card" },
    h(
      "header",
      {},
      h("div", { class: "network-tun-title" }, h("h3", { text: titleOf(tunnel) }), tunnel.id && copyChip(tunnel.id, `${tunnel.id.slice(0, 8)}…`)),
      h(
        "div",
        { class: "network-key-facts" },
        tunnel.connections === null ? pill(listKnown ? "Not on this account's list" : "Connections not known", "") : connected ? pill(`Connected, ${plural(count, "connection")}`, "good") : pill("Not connected", ""),
        (tunnel.running.length > 0 || tunnel.asService) && pill(tunnel.asService ? "Runs here as a service" : "Runs here now", "accent"),
        tunnel.hasCredentials ? pill("Can run here", "") : pill("No credentials here", ""),
        tunnel.created_at && !tunnel.created_at.startsWith("0001") && h("span", { class: "network-tun-age", text: `made ${relativeTime(tunnel.created_at)}` }),
      ),
    ),
    picture(tunnel),
    healthBlock(health),
    routesBlock(tunnel),
    h(
      "footer",
      {},
      health === undefined && canAsk && button({ label: "Check its health", glyph: "chart", small: true, title: "Asks Cloudflare how many copies run, on which versions, and checks this machine's part", onclick: () => onHealth(tunnel) }),
      h("span", { class: "spacer" }),
      button({ label: tunnel.running.length > 0 ? "Run another copy" : "Run it here", glyph: "play", small: true, tone: tunnel.hasCredentials && tunnel.running.length === 0 && !tunnel.asService ? "primary" : "plain", onclick: () => onRun(tunnel) }),
    ),
  );
}
