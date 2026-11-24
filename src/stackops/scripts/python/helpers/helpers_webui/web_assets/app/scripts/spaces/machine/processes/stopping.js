import { stopProcesses } from "./api.js";
import { keyOf } from "./model.js";

// Sends a confirmed stop and says what came of it: one entry per process, as the banner shows them, and whether StackOps itself went.
// Stopping StackOps, or what it runs inside, can cut the answer off. That is the stop working, so it is not passed on as a failure.
// A server that was asked to quit is still there when it answers and goes right after, so for the server itself "still running" is told as stopped.
export async function carryOut({ processes, force }) {
  const named = new Map(processes.map((process) => [process.key, process]));
  const hosts = processes.filter((process) => process.role === "server" || process.role === "server_parent");
  try {
    const { results } = await stopProcesses(processes, force);
    const entries = results.map((result) => {
      const process = named.get(keyOf(result));
      const leaving = process.role === "server" && result.outcome === "still_running";
      return { key: process.key, name: process.name, pid: result.pid, outcome: leaving ? "stopped" : result.outcome, error: result.error };
    });
    return { entries, ended: entries.some((entry) => entry.outcome === "stopped" && hosts.includes(named.get(entry.key))) };
  } catch (error) {
    if (hosts.length === 0) throw error;
    return { entries: [], ended: true };
  }
}
