import { request } from "/assets/scripts/state.js";

export const readStartup = () => request("GET", "/api/machine/autostart");
export const readDetail = (id) => request("GET", `/api/machine/autostart/detail?${new URLSearchParams({ id })}`);
// `action` is one of turn-off, turn-on, remove and put-back. The server checks it against a fresh read before it does anything.
export const change = (action, id) => request("POST", `/api/machine/autostart/${action}`, { id });
