// One list of tunnels from what Cloudflare says about the account and what this machine holds: its configuration files, the credentials
// files in ~/.cloudflared and the copies running right now. `connections` is null while Cloudflare has not been asked or did not answer.
const ID = /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/;

export const titleOf = (tunnel) => tunnel.name || `${tunnel.id.slice(0, 8)}…`;
// What the commands are given to name a tunnel: its name where it has one, or else its ID.
export const handleOf = (tunnel) => tunnel.name || tunnel.id;
export const isConnected = (tunnel) => (tunnel.connections?.length ?? 0) > 0;
export const isHere = (tunnel) => tunnel.hasCredentials || tunnel.configured || tunnel.asService || tunnel.running.length > 0;

const unlisted = (handle) => ({ id: ID.test(handle) ? handle : "", name: ID.test(handle) ? "" : handle, created_at: "", connections: null, inAccount: false });
const onThisMachine = () => ({ hasCredentials: false, configured: false, asService: false, routes: [], running: [] });

// Without the account's list a tunnel named in the configuration and the same tunnel's credentials file cannot be told to be one, since
// the first goes by name and the second by ID: they then show as two.
export function mergeTunnels(local, account) {
  const tunnels = (account ?? []).map((tunnel) => ({ ...tunnel, inAccount: true, ...onThisMachine() }));
  const named = (handle) => {
    let found = tunnels.find((tunnel) => tunnel.id === handle || tunnel.name === handle);
    if (!found) tunnels.push((found = { ...unlisted(handle), ...onThisMachine() }));
    return found;
  };
  for (const id of local.credentials) named(id).hasCredentials = true;
  if (local.service_config.tunnel) Object.assign(named(local.service_config.tunnel), { asService: local.service_active, routes: local.service_config.routes });
  // The file a tunnel started by hand reads wins over the installed service's, where it names routes of its own.
  if (local.config.tunnel) {
    const tunnel = named(local.config.tunnel);
    tunnel.configured = true;
    if (local.config.routes.length > 0) tunnel.routes = local.config.routes;
  }
  for (const process of local.running) {
    const handle = process.tunnel || local.config.tunnel;
    if (handle) named(handle).running.push(process);
  }
  return tunnels.sort((left, right) => isConnected(right) - isConnected(left) || isHere(right) - isHere(left) || titleOf(left).localeCompare(titleOf(right)));
}

// The connections of a tunnel, counted by the city each one reaches. Cloudflare names a data centre by its airport code and a number
// (syd01, syd03); the number is dropped, so one city is one group.
export function placesOf(tunnel) {
  const places = new Map();
  for (const connection of tunnel.connections ?? []) {
    const place = connection.place.replace(/\d+$/, "").toUpperCase() || "?";
    places.set(place, (places.get(place) ?? 0) + 1);
  }
  return [...places].sort((left, right) => right[1] - left[1]);
}

// How well a tunnel would survive losing a machine, from how many copies of it run. One copy holds four connections.
export function redundancyOf(health) {
  if (health.connector_count === 0) return { tone: "", text: "No copy of this tunnel is running anywhere, so nothing it publishes can be reached." };
  if (health.connector_count === 1) return { tone: "warn", text: "One copy is running. If that machine stops, everything this tunnel publishes goes down with it." };
  return { tone: "good", text: `${health.connector_count} copies are running, so one machine can stop and the tunnel stays up.` };
}
