import { request } from "/assets/scripts/state.js";

const BASE = "/api/machine/processes";
const named = ({ pid, started }) => ({ pid, started });

export const readProcesses = (fresh) => request("GET", `${BASE}/list${fresh ? "?fresh=1" : ""}`);
export const readDetail = (process) => request("GET", `${BASE}/detail?${new URLSearchParams(named(process))}`);
export const stopProcesses = (processes, force) => request("POST", `${BASE}/stop`, { targets: processes.map(named), force });
