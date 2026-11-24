// The Network page's own views: where each one lives, and the command paths they stand in for.
export const API = "/api/network";
export const HASHES = { ssh: "#/network/ssh", forwards: "#/network/forwards", wifi: "#/network/wifi", warp: "#/network/warp", tunnels: "#/network/tunnels" };
export const PATHS = {
  setup: "devops network ssh install-server",
  addKey: "devops network ssh add-key",
  debug: "devops network ssh debug",
  mapPort: "devops network ssh map-port",
  wifi: "devops network device connect-wifi",
  warp: "devops network cloudflare connect-warp",
  switchAddress: "devops network cloudflare switch-public-ip",
  tunnelStatus: "devops network cloudflare tunnel-status",
  runTunnel: "devops network cloudflare run-tunnel",
  address: "devops network show-address",
};

// The cards on the Network page's overview. Two of them stand for two commands each, which share one view.
export const ACCESS_CARDS = [
  { id: "ssh", href: HASHES.ssh, emoji: "🔐", name: PATHS.setup, title: "SSH access", blurb: "Who can sign in to this machine over SSH, and how to switch it on." },
  { id: "forwards", href: HASHES.forwards, emoji: "🔀", name: PATHS.mapPort, title: "Forward a port", blurb: "Reach a port on another machine as if it were on this one." },
  { id: "wifi", href: HASHES.wifi, emoji: "📶", name: PATHS.wifi, title: "Wi-Fi", blurb: "The network this machine is on, and the ones it can join." },
  { id: "warp", href: HASHES.warp, emoji: "🔌", name: PATHS.warp, title: "Cloudflare WARP", blurb: "Send traffic through Cloudflare and watch your address change." },
  { id: "tunnels", href: HASHES.tunnels, emoji: "🚇", name: PATHS.tunnelStatus, title: "Cloudflare tunnels", blurb: "Which tunnels exist, where each is connected, and a way to run one." },
];

const WARP_WORDS = { connected: "On", connecting: "Connecting", disconnected: "Off", not_installed: "Not installed", registration_missing: "Not registered yet", daemon_down: "Its service is not running", unable: "Cannot connect", unreadable: "Not answering" };

// How things stand for each card, in a few words, from one reading of this machine (`network_glance.py`). `tone` colours the words.
export const GLANCE_WORDS = {
  ssh: ({ keys }) => ({ text: keys === 0 ? "No key allowed yet" : `${keys} ${keys === 1 ? "key" : "keys"} allowed`, tone: "" }),
  forwards: ({ forwards }) => ({ text: forwards === 0 ? "None running" : `${forwards} running`, tone: forwards > 0 ? "accent" : "" }),
  wifi: ({ wifi, wifi_adapter: adapter, wifi_on: on }) => ({ text: wifi.connected ? (wifi.name ? `On ${wifi.name}` : "Connected") : !adapter ? "No Wi-Fi adapter" : on ? "Not connected" : "Switched off", tone: wifi.connected ? "good" : "" }),
  warp: ({ warp }) => ({ text: WARP_WORDS[warp], tone: warp === "connected" ? "good" : "" }),
  tunnels: ({ cloudflared, tunnels_running: running }) => ({ text: !cloudflared ? "cloudflared is not installed" : running === 0 ? "None running here" : `${running} running here`, tone: running > 0 ? "good" : "" }),
};

// Goes to one of the views. When the address is already there it does not change, so the page is told to show itself again.
export function go(hash) {
  if (location.hash === hash) window.dispatchEvent(new HashChangeEvent("hashchange"));
  else location.hash = hash;
}

export const SIGNAL_WORDS = [[75, "Excellent"], [50, "Good"], [25, "Fair"], [0, "Weak"]];
export const signalWord = (percent) => SIGNAL_WORDS.find(([floor]) => percent >= floor)[1];
