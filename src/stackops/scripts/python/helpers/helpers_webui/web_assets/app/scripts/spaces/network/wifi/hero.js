import { h } from "/assets/scripts/dom.js";
import { copyChip, skeleton } from "../../../widgets.js";
import { fill, reason, signalBars } from "../kit.js";
import { signalWord } from "../words.js";

const STANDARDS = { "802.11be": "Wi-Fi 7", "802.11ax": "Wi-Fi 6", "802.11ac": "Wi-Fi 5", "802.11n": "Wi-Fi 4" };
const fact = (label, value) => value && h("div", { class: "network-fact" }, h("span", { text: label }), h("strong", {}, value));

// The connection as it stands: bars for the signal, the network's name where the system gives it, and the facts around it. The signal can
// arrive after the rest (on a Mac it takes seconds), so the bars start out unlit and fill in.
export function createWifiHero() {
  const element = h("section", { class: "network-hero network-wifi-hero" }, skeleton(1, "card"));

  function paint({ overview, signal, signalPending, address }) {
    const { current, adapter, radio_on: radioOn, problem } = overview;
    if (problem) {
      element.replaceChildren(h("div", { class: "network-hero-top" }, signalBars(null, "big"), h("div", { class: "network-hero-text" }, h("h2", { text: "No Wi-Fi to show" }), h("p", { text: problem }))));
      return;
    }
    const title = current.connected ? current.name || "Connected to Wi-Fi" : radioOn ? "Not connected to a network" : "Wi-Fi is switched off";
    const body = current.connected
      ? signal
        ? `${signalWord(signal.percent)} signal${signal.dbm === null ? `, ${signal.percent}%` : `, ${signal.dbm} dBm`}.`
        : signalPending
          ? "Reading the signal…"
          : "This system did not say how strong the signal is."
      : radioOn
        ? "The adapter is on and waiting for a network."
        : "Switch it on in the system's own Wi-Fi settings.";
    fill(
      element,
      h(
        "div",
        { class: `network-hero-top ${current.connected ? "good" : ""}` },
        signalBars(current.connected && signal ? signal.percent : null, "big"),
        h("div", { class: "network-hero-text" }, h("h2", { text: title }), h("p", { text: body })),
        current.connected && signal && h("div", { class: "network-wifi-meter", title: `${signal.percent}% of full strength` }, h("i", { style: `--share:${signal.percent / 100}` })),
      ),
      current.name_hidden && reason("macOS gives a network's name only to apps with location access. Everything else about the connection is real."),
      h(
        "div",
        { class: "network-facts" },
        fact("Security", current.security),
        fact("Kind", signal?.standard && (STANDARDS[signal.standard] ? `${STANDARDS[signal.standard]} (${signal.standard})` : signal.standard)),
        fact("Channel", signal?.channel),
        fact("Link speed", signal?.rate),
        fact("Background noise", signal && signal.noise !== null && `${signal.noise} dBm`),
        fact("Adapter", adapter),
        fact("Address here", address && copyChip(address)),
      ),
    );
  }

  return { element, paint };
}
