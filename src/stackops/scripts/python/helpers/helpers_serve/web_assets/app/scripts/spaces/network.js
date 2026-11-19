import { h } from "/assets/scripts/dom.js";
import { createLivePanel } from "../live_panel.js";
import { rise } from "../motion.js";
import { createView, toolButton, toolGrid } from "../space_kit.js";
import { copyChip, glyphTile, notice, pill, sectionHead } from "../widgets.js";
import { plural } from "../words.js";

const SHARE_TOOLS = ["devops network share-server", "devops network share-terminal", "devops network send", "devops network receive", "devops network share-temp-file", "devops network vscode-share"];
const ACCESS_TOOLS = [
  "devops network ssh install-server", "devops network ssh add-key", "devops network ssh debug", "devops network ssh map-port", "devops network device connect-wifi",
  "devops network cloudflare connect-warp", "devops network cloudflare tunnel-status", "devops network cloudflare run-tunnel",
];

export function createNetworkSpace({ tools }) {
  const address = (label, hue, glyph, value, note) =>
    h("article", { class: "address-card lit" }, glyphTile(glyph, hue, 42), h("span", { class: "stat-label", text: label }), value ? copyChip(value) : h("strong", { class: "dim", text: "Unavailable" }), h("span", { class: "dim", text: note }));

  const panel = createLivePanel({
    title: "This machine on the network", path: "devops network show-address", extra: ["--json"], skeletonShape: "card",
    render: (data, { setCount }) => {
      if (!data?.interfaces) return notice({ glyph: "globe", title: "No network details", body: "This machine did not report any addresses." });
      const interfaces = data.interfaces.filter((item) => item.interface !== data.lan?.interface);
      setCount(plural(data.interfaces.length, "connection"));
      const publicAddress = data.public?.ip ?? data.public?.ip_address ?? (typeof data.public === "string" ? data.public : null);
      return h(
        "div",
        { class: "stack" },
        rise(
          h(
            "div",
            { class: "address-grid" },
            address("On your local network", 200, "globe", data.lan?.ipv4_address, data.lan ? `through ${data.lan.interface}` : "Not connected"),
            address("On the internet", 252, "share", publicAddress, publicAddress ? "what other networks see" : "could not be looked up right now"),
            address("Hardware address", 150, "cpu", data.lan?.mac_address, "identifies this device locally"),
          ),
        ),
        interfaces.length > 0 &&
          h(
            "div",
            { class: "interface-row" },
            interfaces.map((item) => h("span", { class: "interface" }, pill(item.interface, ""), copyChip(item.ipv4_address))),
          ),
      );
    },
  });

  const element = createView(
    {
      title: "Network", lede: "Where this machine lives on the network, and quick ways to share with others.",
      actions: [toolButton(tools, "devops network share-server", { label: "Share a folder", glyph: "share", tone: "primary" })],
    },
    panel.element,
    h("section", { class: "block" }, sectionHead("Share"), toolGrid(tools, SHARE_TOOLS)),
    h("section", { class: "block" }, sectionHead("Remote access"), toolGrid(tools, ACCESS_TOOLS)),
  );
  return { element, show: () => panel.ensure() };
}
