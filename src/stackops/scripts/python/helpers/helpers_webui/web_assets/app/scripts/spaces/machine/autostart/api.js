import { request } from "/assets/scripts/state.js";

export const readStartup = () => request("GET", "/api/machine/autostart");
export const readDetail = (id) => request("GET", `/api/machine/autostart/detail?${new URLSearchParams({ id })}`);
// `action` is one of turn-off, turn-on, remove and put-back. The server checks it against a fresh read before it does anything.
export const change = (action, id) => request("POST", `/api/machine/autostart/${action}`, { id });
// One of the scripts the Scripts page lists from the folder `base`, named by its file. The server looks it up afresh before it adds it.
export const addScript = (base, path) => request("POST", "/api/machine/autostart/scripts", { base, path });
