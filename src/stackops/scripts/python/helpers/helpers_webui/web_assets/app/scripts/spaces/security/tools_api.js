import { request as send, state } from "/assets/scripts/state.js";

const STALE_SERVER = "The web UI server was started before this tool was added to it. Stop it and start it again, then reload this page.";

// The page's scripts are read from disk on every load, the server's own code only when it starts. So a server that has been running since
// before these tools arrived answers their calls with "not found", and that is said in words that tell what to do about it.
async function request(method, path, body, signal) {
  try {
    return await send(method, path, body, signal);
  } catch (error) {
    if (error.status === 404 && !error.payload) throw new Error(STALE_SERVER);
    throw error;
  }
}

// Typed paths are read from the working folder, as the path suggestions read them.
const within = (parameters) => new URLSearchParams({ ...parameters, base: state.settings.workingDirectory });

// The saved scans, each with how many of its apps could be installed, and the folder apps are installed in.
export const readRuns = () => request("GET", "/api/security/scans/runs");
export const readInstallPlan = (run) => request("GET", `/api/security/scans/install-plan?${new URLSearchParams({ run })}`);
export const readExportPlan = (run) => request("GET", `/api/security/scans/export-plan?${new URLSearchParams({ run })}`);
export const checkExportPlace = (path) => request("GET", `/api/security/scans/export-place?${within({ path })}`);
export const exportRun = (run, output) => request("POST", "/api/security/scans/export", { run, output, base: state.settings.workingDirectory });

// Which cloud an upload goes to, read from this machine alone. Whether that cloud answers goes over the network, so it is a call of its own.
export const readCloud = () => request("GET", "/api/security/cloud/state");
export const readCloudReach = () => request("GET", "/api/security/cloud/reach");
export const readUploadPlan = (path) => request("GET", `/api/security/cloud/upload-plan?${within({ path })}`);
export const readDownloadPlace = () => request("GET", "/api/security/cloud/download-place");
// A link lets whoever holds it fetch the file, so it travels in the body, not in the address.
export const checkDriveLink = (text, signal) => request("POST", "/api/security/cloud/drive-link", { text }, signal);

export const readLocker = () => request("GET", "/api/security/locker/state");
export const lookAt = ({ mode, path, compression, output }) => request("GET", `/api/security/locker/look?${within({ mode, path, compression, output })}`);
// The only call that carries a password. It goes in the body of this one request and is kept nowhere on the page after it.
export const runWithPassword = (run) => request("POST", "/api/security/locker/run", { ...run, base: state.settings.workingDirectory });
