import { h, icon } from "/assets/scripts/dom.js";
import { request } from "/assets/scripts/state.js";
import { agentButton } from "../agent_ask.js";
import { PLACES } from "../agent_places.js";
import { staleKeeper } from "../data.js";
import { partLoaders } from "../features.js";
import { createLivePanel } from "../live_panel.js";
import { rise } from "../motion.js";
import { createParts, linkCard, toolButton, toolGrid, viewHead } from "../space_kit.js";
import { copyChip, glyphTile, notice, pill, sectionHead } from "../widgets.js";
import { plural } from "../words.js";
import { openChecks, passedPills, summaryText } from "./network/ssh/checks.js";
import { ACCESS_CARDS, API, GLANCE_WORDS, HASHES } from "./network/words.js";

const SHARE_TOOLS = ["devops network share-server", "devops network share-terminal", "devops network send", "devops network receive", "devops network share-temp-file", "devops network vscode-share"];

// Views that swap in place: the overview at #/network, and the ones features.js lists for this page (SSH access, port forwards, Wi-Fi,
// WARP and Cloudflare tunnels), each at an address of its own under it.
export function createNetworkSpace(context) {
  const { activity, tools } = context;
  const address = (label, hue, glyph, value, note) =>
    h("article", { class: "address-card lit" }, glyphTile(glyph, hue, 42), h("span", { class: "stat-label", text: label }), value ? copyChip(value) : h("strong", { class: "dim", text: "Unavailable" }), h("span", { class: "dim", text: note }));

  const panel = createLivePanel({
    title: "This machine on the network", path: "devops network show-address", extra: ["--json"], skeletonShape: "card", tunable: false,
    render: (data, { setCount }) => {
      if (!data?.interfaces) return notice({ glyph: "globe", title: "No network details", body: "This machine did not report any addresses." });
      const interfaces = data.interfaces.filter((item) => item.interface !== data.lan?.interface);
      setCount(plural(data.interfaces.length, "connection"));
      const place = data.public && [data.public.city, data.public.country_name, data.public.org].filter(Boolean).join(" · ");
      return h(
        "div",
        { class: "stack" },
        rise(
          h(
            "div",
            { class: "address-grid" },
            address("On your local network", 200, "globe", data.lan?.ipv4_address, data.lan ? `through ${data.lan.interface}` : "Not connected"),
            address("On the internet", 252, "share", data.public?.ip, data.public ? place || "what other networks see" : data.public_error),
            address("Hardware address", 150, "cpu", data.lan?.mac_address, "identifies this device locally"),
          ),
        ),
        interfaces.length > 0 &&
          h(
            "div",
            { class: "interface-row" },
            interfaces.map((item) => h("span", { class: "interface" }, pill(item.interface, ""), copyChip(item.ipv4_address), item.mac_address && copyChip(item.mac_address))),
          ),
      );
    },
  });

  // The SSH check only reads. The SSH page shows the same checks as steps, with the keys and the setup beside them.
  const access = createLivePanel({
    title: "Remote access", path: "devops network ssh debug", extra: ["--json"], tunable: false,
    actions: [h("a", { class: "btn small ghost", href: HASHES.ssh, title: "Whose keys are allowed, and how to switch SSH on" }, icon("key", 14), h("span", { text: "Keys and setup" }))],
    render: ({ checks, summary }, { setCount }) => {
      const fine = passedPills(checks);
      setCount(summaryText(summary));
      return h("div", { class: "stack" }, fine.length > 0 && h("div", { class: "project-facts" }, fine), openChecks(checks));
    },
  });

  // Each card says in a few words how its subject stands, from one quick reading of this machine. A reading that fails leaves the cards
  // as plain links, which they are without it.
  const stands = new Map();
  const cards = h(
    "div",
    { class: "tool-grid" },
    ACCESS_CARDS.map((card) => {
      const element = linkCard(card);
      stands.set(card.id, element.querySelector(".tool-card-text").appendChild(h("em", { class: "network-glance" })));
      return element;
    }),
  );
  const glance = staleKeeper(cards, async () => {
    const answer = await request("GET", `${API}/glance`).catch(() => null);
    if (answer === null) return glance.spoil();
    for (const [id, stand] of stands) {
      const { text, tone } = GLANCE_WORDS[id](answer);
      stand.textContent = text;
      stand.className = `network-glance ${tone}`;
    }
  });

  const overview = h(
    "div",
    {},
    viewHead({
      title: "Network", lede: "Where this machine lives on the network, and quick ways to share with others.",
      actions: [agentButton(activity, PLACES.network), toolButton(tools, "devops network share-server", { label: "Share a folder", glyph: "share", tone: "primary" })],
    }),
    panel.element,
    h("section", { class: "block" }, sectionHead("Share"), toolGrid(tools, SHARE_TOOLS)),
    access.element,
    h("section", { class: "block" }, sectionHead("Set up and connect"), cards),
  );
  const show = () => {
    panel.ensure();
    access.ensure();
    glance.ensure();
  };
  const element = h("section", { class: "view", hidden: true }, overview);
  return { element, show: createParts({ element, built: { "": { element: overview, show } }, loaders: partLoaders("network"), context }) };
}
