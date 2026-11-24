import { request } from "/assets/scripts/state.js";

// The Windows page's own calls. `act` answers with one result per window: done, gone (it closed meanwhile) or failed with the reason.
// `openPermissionSettings` opens System Settings on the serving machine's screen, at the list of apps macOS allows to see and move windows.
export const windowsApi = {
  list: () => request("GET", "/api/machine/windows"),
  act: (action, ids) => request("POST", "/api/machine/windows/action", { action, ids }),
  openPermissionSettings: () => request("POST", "/api/machine/windows/permission", {}),
};
