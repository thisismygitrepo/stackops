import { formatBytes, humanize, plural } from "../../../words.js";

export const PROCESSES_HASH = "#/machine/processes";
export const TOOL_PATH = "utils machine kill-process";
export const REFRESH_MILLISECONDS = 3000;
// What counts as heavy: a quarter of one processor core, and one gigabyte of memory. The quick filters and the warm bars both go by these.
export const HEAVY_CPU = 25;
export const HEAVY_MEMORY = 1024 ** 3;

// The words for a process's state as the system reports it. One that is not listed is shown under its own name.
const STATUSES = {
  running: { label: "Running", tone: "busy", hint: "Doing work, or ready to as soon as the processor is free." },
  sleeping: { label: "Waiting", tone: "", hint: "Waiting for something to do." },
  waiting: { label: "Waiting", tone: "", hint: "Waiting for something to do." },
  idle: { label: "Idle", tone: "", hint: "Doing nothing right now." },
  stopped: { label: "Paused", tone: "held", hint: "Something paused it. It does nothing until it is resumed." },
  suspended: { label: "Paused", tone: "held", hint: "Something paused it. It does nothing until it is resumed." },
  "tracing-stop": { label: "Paused by a debugger", tone: "held", hint: "A debugger is holding it." },
  "disk-sleep": { label: "Waiting on the disk", tone: "", hint: "Waiting for a read or a write to finish." },
  locked: { label: "Waiting on a lock", tone: "", hint: "Waiting for something another process holds." },
  waking: { label: "Waking up", tone: "", hint: "About to run." },
  "wake-kill": { label: "Waking up", tone: "", hint: "About to run." },
  parked: { label: "Parked", tone: "", hint: "Set aside by the system." },
  zombie: { label: "Ended", tone: "ended", hint: "It has ended. It stays listed until the program that started it collects it." },
  dead: { label: "Ended", tone: "ended", hint: "It has ended." },
};

export const statusOf = (status) => STATUSES[status] ?? { label: humanize(status), tone: "", hint: "" };

// What a process is to this machine or to this app, when that matters before stopping it.
export const ROLES = {
  system: { label: "System", tone: "", risky: true, warning: "Part of the operating system. Stopping it can log you out, freeze the screen or restart a service." },
  server: { label: "StackOps", tone: "accent", risky: true, warning: "This is StackOps itself. Stopping it ends this page." },
  server_parent: { label: "Runs StackOps", tone: "accent", risky: true, warning: "StackOps runs inside this. Stopping it can end StackOps and this page with it." },
  server_child: { label: "StackOps task", tone: "accent", risky: false, warning: "StackOps started this. Stopping it ends a task this app is running." },
};

export const LOCKS = {
  ended: "It has already ended. It leaves the list when the program that started it collects it or stops.",
  foreign: "It belongs to another account, and StackOps does not run as an administrator, so it cannot stop it.",
};

export const OUTCOMES = {
  stopped: { tone: "good", text: "stopped" },
  still_running: { tone: "warn", text: "still running" },
  already_gone: { tone: "", text: "had already ended" },
  not_allowed: { tone: "bad", text: "not allowed" },
  failed: { tone: "bad", text: "could not be stopped" },
};

export const cpuText = (value) => (value === null || value === undefined ? "—" : `${value < 9.95 ? value.toFixed(1) : Math.round(value).toLocaleString()}%`);
export const memoryText = (bytes) => (bytes === null || bytes === undefined ? "—" : formatBytes(bytes));
export const countText = (count, word = "process") => (word === "process" ? `${count.toLocaleString()} process${count === 1 ? "" : "es"}` : plural(count, word));

// How long ago a process started, short enough for a column.
export function ageText(started, now) {
  const seconds = Math.max(0, now - started);
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} h ago`;
  const days = Math.floor(seconds / 86400);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}

export const startedText = (started) => new Date(started * 1000).toLocaleString([], { dateStyle: "medium", timeStyle: "medium" });

// The filters another view can open this page with, by the command's parameter names. Each one is shown as a chip that can be taken off again.
// They match the way the command does: a command by any part of it, a size or a share as a minimum, everything else exactly.
const GIVEN = {
  command: (text) => ({ label: `Command has “${text}”`, test: (process) => process.command.toLowerCase().includes(text.toLowerCase()) }),
  name: (text) => ({ label: `Named ${text}`, test: (process) => process.name === text }),
  username: (text) => ({ label: `Owned by ${text}`, test: (process) => process.user === text }),
  status: (text) => ({ label: statusOf(text).label, test: (process) => process.status === text }),
  pid: (text) => ({ label: `ID ${text}`, test: (process) => process.pid === Number(text) }),
  port: (text) => ({ label: `Port ${text}`, test: (process) => process.ports.includes(Number(text)) }),
  memory: (text) => ({ label: `${formatBytes(Number(text) * 1024 ** 2)} or more`, test: (process) => (process.memory ?? 0) >= Number(text) * 1024 ** 2 }),
  cpu: (text) => ({ label: `${Number(text)}% CPU or more`, test: (process) => (process.cpu ?? 0) >= Number(text) }),
};

export function givenFilters(preset) {
  return Object.entries(preset ?? {})
    .filter(([name, value]) => GIVEN[name] && value !== null && value !== undefined && String(value).trim() !== "")
    .map(([name, value]) => ({ name, ...GIVEN[name](String(value).trim()) }));
}
