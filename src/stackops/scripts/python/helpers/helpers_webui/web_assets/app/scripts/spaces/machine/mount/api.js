import { request, state } from "/assets/scripts/state.js";

// The devices as the command lists them, each with whether and how it can be mounted on this machine.
export const readPicture = () => request("GET", "/api/machine/mount/devices");

// What a typed folder (`kind` "folder") or key file ("key") names, read from the working folder as the path suggestions are.
export const checkPlace = (path, kind) => request("GET", `/api/machine/mount/place?${new URLSearchParams({ path, kind, base: state.settings.workingDirectory })}`);
