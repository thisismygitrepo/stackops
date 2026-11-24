// The purpose-built views of the Network page, in the shape features.js describes. `load` paths are relative to this folder.
// Seven commands, five pages: the two SSH commands share the SSH page and the two tunnel commands share the tunnels page.
export const NETWORK_FEATURES = [
  { path: "devops network ssh install-server", space: "network", part: "ssh", load: () => import("../spaces/network/ssh.js") },
  { path: "devops network ssh add-key", space: "network", part: "ssh", load: () => import("../spaces/network/ssh_add_key.js") },
  { path: "devops network ssh map-port", space: "network", part: "forwards", load: () => import("../spaces/network/forwards.js") },
  { path: "devops network device connect-wifi", space: "network", part: "wifi", load: () => import("../spaces/network/wifi.js") },
  { path: "devops network cloudflare connect-warp", space: "network", part: "warp", load: () => import("../spaces/network/warp.js") },
  { path: "devops network cloudflare tunnel-status", space: "network", part: "tunnels", load: () => import("../spaces/network/tunnels.js") },
  { path: "devops network cloudflare run-tunnel", space: "network", part: "tunnels", load: () => import("../spaces/network/tunnels.js") },
];
