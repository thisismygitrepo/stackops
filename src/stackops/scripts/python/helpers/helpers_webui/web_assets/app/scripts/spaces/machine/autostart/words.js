export const AUTOSTART_HASH = "#/machine/autostart";
export const COMMAND = "utils machine autostart";
export const PROCESSES_COMMAND = "utils machine kill-process";

// The command's categories, in its order. `option` is the word the command takes for it.
export const KINDS = {
  "remote-access": { label: "Network", long: "Network and remote access", glyph: "globe", hue: 205, option: "network" },
  "containers-storage": { label: "Storage", long: "Containers and storage", glyph: "database", hue: 28, option: "storage" },
  "apps-services": { label: "Apps", long: "Apps and their helpers", glyph: "apps", hue: 262, option: "apps" },
  "monitoring-hardware": { label: "Monitoring", long: "Monitoring and hardware", glyph: "chart", hue: 45, option: "monitoring" },
  "desktop-session": { label: "Desktop", long: "Desktop and session", glyph: "monitor", hue: 150, option: "desktop" },
  "system-os": { label: "System", long: "System", glyph: "cpu", hue: 225, option: "system" },
  other: { label: "Other", long: "Other", glyph: "cube", hue: 320, option: "other" },
};

export const SCOPES = {
  boot: { label: "When the computer starts", moment: "when the computer starts", glyph: "power" },
  login: { label: "When you sign in", moment: "when you sign in", glyph: "key" },
};

// `slot` picks the colour in the picture of when things start (machine_autostart.css). The order is fixed, so a colour always means the same thing.
export const MANNERS = {
  always: { label: "Right away", lower: "right away", hint: "They start by themselves, with nothing asking for them.", slot: 1 },
  timer: { label: "On a timer", lower: "on a timer", hint: "They run at set times or every so often.", slot: 2 },
  demand: { label: "When needed", lower: "when needed", hint: "They wait until something asks for them or something they watch happens.", slot: 3 },
};

export const STATES = {
  running: { label: "Running now", short: "Running", tone: "good", glyph: "play" },
  resting: { label: "Not running", short: "Not running", tone: "", glyph: "clock" },
  off: { label: "Turned off", short: "Off", tone: "", glyph: "power" },
  trouble: { label: "Stopped with an error", short: "Error", tone: "warn", glyph: "alert" },
};

export const systemName = (platform) => (platform === "Linux" ? "the system" : platform);

export const whoseWords = (platform) => ({
  yours: { label: "Yours", hint: "Added for your account." },
  apps: { label: "Installed by apps", hint: "Installed for every account on this computer, by an app or an administrator." },
  system: { label: `Part of ${systemName(platform)}`, hint: "Comes with the operating system." },
});

export const ORDERS = [["name", "Name"], ["owner", "Belongs to"], ["running", "Running first"]];
export const GROUPINGS = [["when", "When"], ["whose", "Whose"], ["kind", "Kind"], ["none", "One list"]];

const UNITS = [[86400, "day"], [3600, "hour"], [60, "minute"], [1, "second"]];
const WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const twoDigits = (value) => String(value).padStart(2, "0");
const capital = (text) => text.charAt(0).toUpperCase() + text.slice(1);

// In the largest unit that divides it: 300 seconds is "every 5 minutes", 90 is "every 90 seconds".
export function everyText(seconds) {
  const [size, unit] = UNITS.find(([span]) => seconds >= span && seconds % span === 0);
  return seconds === size ? `every ${unit}` : `every ${seconds / size} ${unit}s`;
}

// One of a job's set times, the way launchd reads it: a part that is left out means every one of them.
export function slotText({ month, day, weekday, hour, minute }) {
  const time = hour !== null ? (minute === null ? `every minute from ${twoDigits(hour)}:00 to ${twoDigits(hour)}:59` : `at ${twoDigits(hour)}:${twoDigits(minute)}`) : minute === null ? "every minute" : `every hour at ${minute} past`;
  const days = [weekday !== null && `${WEEKDAYS[weekday] ?? `weekday ${weekday}`}s`, day !== null && `day ${day} of the month`, month !== null && `in ${MONTHS[month - 1] ?? `month ${month}`}`].filter(Boolean);
  return capital(days.length ? `${days.join(", ")} ${time}` : hour !== null ? `every day ${time}` : time);
}

const everyOf = (entry) => {
  const found = entry.triggers.map((trigger) => /^every (\d+)s$/.exec(trigger)).find(Boolean);
  return found ? everyText(Number(found[1])) : "";
};

// One line for the list: when the entry starts, in the fewest words that are still true.
export function whenText(entry) {
  const { moment } = SCOPES[entry.scope];
  if (entry.kind === "login_item" || entry.kind === "sign_in") return `Opens ${moment}`;
  if (entry.kind === "listed" || entry.kind === "systemd") return `Starts ${moment}`;
  const timed = everyOf(entry) || (entry.triggers.includes("scheduled") ? "at set times" : "");
  if (entry.triggers.includes("kept alive")) return `Starts ${moment} and is kept running`;
  if (entry.triggers.includes("at load")) return timed ? `Starts ${moment}, then again ${timed}` : `Starts ${moment}`;
  if (timed) return `Runs ${timed}`;
  return "Starts when it is needed";
}

const TRIGGERS = {
  "kept alive": () => "It is kept running. The system starts it again if it stops.",
  scheduled: (_entry, detail) => (detail?.calendar.length ? detail.calendar.map(slotText) : "At set times"),
  "path changes": () => "When a file or folder it watches changes",
  "queued files": () => "When files arrive in a folder it watches",
  "mount events": () => "When a disk is connected",
  "socket demand": () => "When something connects to it",
  "system events": () => "When the system reports something it waits for",
  "service demand": () => "When another program asks for it",
};

// Everything that starts the entry, one line each, for its detail. `detail` is what the server says about one launchd job; it may not have arrived.
export function triggerLines(entry, detail) {
  if (entry.kind !== "launchd") return [capital(SCOPES[entry.scope].moment)];
  return entry.triggers.flatMap((trigger) => {
    const every = /^every (\d+)s$/.exec(trigger);
    if (trigger === "at load") return capital(SCOPES[entry.scope].moment);
    if (every) return capital(everyText(Number(every[1])));
    return TRIGGERS[trigger]?.(entry, detail) ?? capital(trigger);
  });
}

// What the entry is doing now, for its row and its detail. Nothing when this system does not say.
export function stateWords(entry) {
  const later = entry.scope === "boot" ? "the next time the computer starts" : "at your next sign-in";
  if (!entry.enabled) return { ...STATES.off, text: "It is turned off, so it does not start on its own." };
  if (entry.live === "running") return { ...STATES.running, text: `Running now, as process ${entry.pid}.` };
  if (entry.state === "trouble") return { ...STATES.trouble, text: `It stopped with an error the last time it ran (code ${entry.last_exit}). It is loaded and will be started again when it is due.` };
  if (entry.live === "waiting") return { ...STATES.resting, short: "Ready", text: "Loaded and ready, not running right now." };
  if (entry.live === "idle" && entry.kind === "login_item") return { ...STATES.resting, label: "Not open", short: "Not open", text: "The app is not open right now." };
  if (entry.live === "idle") return { ...STATES.resting, short: "Not loaded", text: `The system has not loaded it yet. It starts ${later}.` };
  return null;
}

export function lastEndText(entry) {
  if (entry.last_exit === null || entry.last_exit === undefined) return "";
  if (entry.last_exit === 0) return "It finished normally.";
  return entry.last_exit > 0 ? `It stopped with an error, code ${entry.last_exit}.` : `Something else stopped it, with signal ${-entry.last_exit}.`;
}

// Why an entry has no switch, by the reason the server gives, with the way forward where there is one.
const LOCKS = {
  system: (_entry, platform) => `It is part of ${systemName(platform)}, so StackOps leaves it alone.`,
  administrator: (entry, platform) =>
    platform === "macOS"
      ? "It starts with this Mac, for every account. Turning it off or removing it takes an administrator password, which StackOps does not ask for. The app it belongs to may have a setting for it, and System Settings lists it under General, Login Items & Extensions."
      : `It starts for every account on this computer${entry.scope === "boot" ? ", when the computer starts" : ""}. Changing that takes administrator rights, which StackOps does not ask for.`,
  managed: () => "It belongs to the software that guards or manages this Mac, so StackOps leaves it alone.",
  unlocated: () => "macOS does not say where this item is, so it cannot be taken off the list from here. System Settings lists it under General, Login Items & Extensions.",
  no_switch: (entry) => `StackOps has no switch for this kind of entry (${entry.source}). Use the system's own tools for it.`,
};

// A server older than this page gives no reason: then the entry is only said to have no switch.
export const lockText = (entry, platform) => (LOCKS[entry.lock] ?? LOCKS.no_switch)(entry, platform);

// What turning an entry off, and back on, does, for the question asked before it is done. A launch agent or a unit is stopped and started
// by the system then and there. A program that is only opened at sign-in is left as it is until the next one.
export function switchWords(entry, platform) {
  const system = platform === "Linux" ? "The system" : platform;
  if (entry.kind === "sign_in") {
    const kept = platform === "Windows" ? "It stays in this list, and in Task Manager under Startup apps" : "Its file stays where it is";
    return {
      off: `${system} no longer opens it when you sign in. If it is open now, it stays open. ${kept}, so you can turn it back on from this page.`,
      on: `${system} opens it again when you sign in, from the next sign-in on.`,
    };
  }
  const now = entry.live === "running" ? `${system} stops it now and` : entry.live === "waiting" && entry.kind === "launchd" ? `${system} unloads it now and` : system;
  const yoursOnly = entry.whose === "apps" ? " That holds for your account only, and the app it belongs to may turn it back on." : "";
  return {
    off: `${now} no longer starts it when you sign in.${yoursOnly} Its file stays where it is, so you can turn it back on from this page.`,
    on:
      entry.kind === "launchd"
        ? `macOS loads it again now, the way it does when you sign in${entry.manner === "always" ? ", so it starts right away" : ""}. From then on it starts on its own at every sign-in.`
        : `${system} starts it now, and from then on at every sign-in.`,
  };
}
