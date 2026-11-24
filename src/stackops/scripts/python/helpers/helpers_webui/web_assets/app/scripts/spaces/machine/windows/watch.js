import { POLL_MILLISECONDS } from "./words.js";

// Reads the windows on request and again every few seconds while `element` is in view, so the page follows what happens on the desktop.
// `read` asks the server; `onAnswer(payload, failure)` is handed each answer that is still wanted. Readings can overlap, and one asked for
// after an action must not be answered by one that began before it, so only the last one asked for reaches the page.
// `idle()` says the page is in a state another reading cannot change, which stops the clock.
export function createWatcher({ element, read, onAnswer, idle }) {
  let ticket = 0;
  let timer = 0;
  const watching = () => element.isConnected && !element.closest("[hidden]") && document.visibilityState === "visible";

  async function load() {
    const mine = (ticket += 1);
    let payload = null;
    let failure = null;
    try {
      payload = await read();
    } catch (error) {
      failure = error;
    }
    if (mine === ticket) onAnswer(payload, failure);
  }

  // The next reading on the clock, `delay` from now. A page that went out of view lets the clock stop; `resume` starts it again.
  function schedule(delay) {
    clearTimeout(timer);
    timer = setTimeout(async () => {
      if (!watching() || idle()) return;
      await load();
      schedule(POLL_MILLISECONDS);
    }, delay);
  }

  function resume() {
    schedule(POLL_MILLISECONDS);
    return load();
  }

  // Coming back to the tab reads the list at once: the desktop has usually changed while the page was out of sight.
  document.addEventListener("visibilitychange", () => watching() && !idle() && resume());
  return { load, schedule, resume };
}
