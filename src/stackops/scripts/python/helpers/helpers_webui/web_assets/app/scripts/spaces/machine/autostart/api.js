import { request } from "/assets/scripts/state.js";

export const readStartup = () => request("GET", "/api/machine/autostart");
export const readDetail = (id) => request("GET", `/api/machine/autostart/detail?${new URLSearchParams({ id })}`);
// `action` is one of turn-off, turn-on, remove and put-back. The server checks it against a fresh read before it does anything.
export const change = (action, id) => request("POST", `/api/machine/autostart/${action}`, { id });
// One of the scripts the Scripts page lists from the folder `base`, named by its file. The server looks it up afresh before it adds it.
// `when` is "login" or "boot", and `systems` are the other systems the startup list is to name it for.
export const addScript = (base, path, when, systems) => request("POST", "/api/machine/autostart/scripts", { base, path, when, systems });
// How this machine differs from the startup list in the dotfiles: what the list names for this system and is not started here, and the
// scripts of the dotfiles that start here without being on it.
export const readRemembered = () => request("GET", "/api/machine/autostart/remembered");
// What `utils machine autostart-apply` does. `prune` also stops what starts here without being on the list.
export const applyRemembered = (prune) => request("POST", "/api/machine/autostart/apply", { prune });
