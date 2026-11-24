import { tildify } from "/assets/scripts/dom.js";
import { request, state as app } from "/assets/scripts/state.js";

export const UPDATE_HASH = "#/machine/update";
export const UPDATE_TOOL = ["devops", "self", "update"];
export const UPDATE_PATH = UPDATE_TOOL.join(" ");
export const UPDATE_TITLE = "Update StackOps";

// The page's switches and the parameter of the command each one stands for. The command refreshes its scripts and settings unless told to skip
// that, so the first switch is on while its parameter is off.
const SWITCHES = [
  { id: "refresh", parameter: "no_copy_assets", flag: "--no-copy-assets", inverted: true },
  { id: "settings", parameter: "sync_configs", flag: "--sync-configs", inverted: false },
  { id: "shell", parameter: "config_shell", flag: "--config-shell", inverted: false },
  { id: "developer", parameter: "dev", flag: "--dev", inverted: false },
];
const isOn = (value) => value === true || value === "true" || value === "on";

// `preset` holds values by the command's parameter names, from whoever opened the page. Anything it leaves out starts the way the command does.
export const optionsFrom = (preset) => Object.fromEntries(SWITCHES.map((item) => [item.id, isOn(preset?.[item.parameter]) !== item.inverted]));
export const runArguments = (options) => [...UPDATE_TOOL, ...SWITCHES.filter((item) => options[item.id] !== item.inverted).map((item) => item.flag)];

// The page's three lookups (machine_update_routes.py). None of them changes anything.
export const readState = () => request("GET", "/api/machine/update/state");
export const readLatest = (fresh) => request("GET", `/api/machine/update/latest${fresh ? "?fresh=1" : ""}`);
export const readEffects = () => request("GET", "/api/machine/update/effects");

export const home = (path) => tildify(path, app.boot.home);
export const shortId = (sha) => sha.slice(0, 9);
// "https://github.com/owner/name.git" and "git@github.com:owner/name.git" both read "github.com/owner/name".
export const remoteName = (address) => address.replace(/^[a-z+]+:\/\//, "").replace(/^[^@/]+@([^:/]+):/, "$1/").replace(/\.git$/, "");

export const dirtyCount = (checkout) => checkout.changed + checkout.untracked;
// The commits the update would bring in: what the last fetch left behind, or what GitHub lists now if that is more.
export const incomingCount = (checkout, latest) => Math.max(checkout.behind, latest?.commits.length ?? 0);
// What "Commit and push my changes first" would push: the commits not pushed yet and the one it makes out of the uncommitted changes.
export const pushCount = (checkout) => checkout.ahead + (dirtyCount(checkout) > 0 ? 1 : 0);
export const isWindowsTool = (state) => app.boot.platform === "Windows" && Boolean(state.installed?.uv_tool);

// What the update leaves for the person to do: the server that draws this page goes on running what it loaded when it started.
export const RESTART_LEDE = "This page comes from the program that was running before the update, and it keeps showing the old version until that program is stopped and started again.";
