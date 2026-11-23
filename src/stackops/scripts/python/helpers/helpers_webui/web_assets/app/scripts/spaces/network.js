import { h } from "/assets/scripts/dom.js";
import { createLivePanel } from "../live_panel.js";
import { rise } from "../motion.js";
import { createView, toolButton, toolGrid } from "../space_kit.js";
import { copyChip, glyphTile, notice, pill, sectionHead } from "../widgets.js";
import { plural } from "../words.js";

const SHARE_TOOLS = ["devops network share-server", "devops network share-terminal", "devops network send", "devops network receive", "devops network share-temp-file", "devops network vscode-share"];
const ACCESS_TOOLS = [
  "devops network ssh install-server", "devops network ssh add-key", "devops network ssh map-port", "devops network device connect-wifi",
  "devops network cloudflare connect-warp", "devops network cloudflare tunnel-status", "devops network cloudflare run-tunnel",
];
const CHECK_PILLS = { error: ["Problem", "bad"], unknown: ["Not confirmed", "warn"] };

export function createNetworkSpace({ tools }) {
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

  // The SSH check only reads. Its suggestions, some of them `sudo` commands, are offered to copy and never run from here.
  const access = createLivePanel({
    title: "Remote access", path: "devops network ssh debug", extra: ["--json"], tunable: false,
    render: ({ checks, summary }, { setCount }) => {
      const fine = checks.filter((check) => check.status === "ok");
      const open = checks.filter((check) => check.status !== "ok").sort((left, right) => (right.status === "error") - (left.status === "error"));
      setCount(summary.ready ? "ready for SSH connections" : [summary.error_count > 0 && plural(summary.error_count, "problem"), summary.unknown_count > 0 && `${summary.unknown_count} not confirmed`].filter(Boolean).join(" · "));
      return h(
        "div",
        { class: "stack" },
        fine.length > 0 && h("div", { class: "project-facts" }, fine.map((check) => pill(check.label, "good"))),
        open.length > 0 &&
          rise(
            h(
              "ul",
              { class: "session-list" },
              open.map((check) =>
                h(
                  "li",
                  { class: "session-row check-row" },
                  h("div", { class: "session-text" }, h("strong", { text: check.label }), h("span", { text: check.message }), check.manual_advice.map((advice) => h("span", { class: "dim", text: advice })), check.command_suggestions.map((command) => copyChip(command))),
                  pill(...CHECK_PILLS[check.status]),
                ),
              ),
            ),
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
    access.element,
    h("section", { class: "block" }, sectionHead("Set up and connect"), toolGrid(tools, ACCESS_TOOLS)),
  );
  return {
    element,
    show: () => {
      panel.ensure();
      access.ensure();
    },
  };
}
