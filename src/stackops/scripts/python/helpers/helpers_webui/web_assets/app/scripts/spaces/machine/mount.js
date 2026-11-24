import { formatClock, h, icon } from "/assets/scripts/dom.js";
import { staleKeeper } from "../../data.js";
import { button, notice } from "../../widgets.js";
import { readPicture } from "./mount/api.js";
import { mountBanner } from "./mount/banner.js";
import { createDeviceList } from "./mount/device_list.js";
import { findDevice, titleOf } from "./mount/model.js";
import { createPlanCard } from "./mount/plan_card.js";
import { runMount } from "./mount/run.js";
import { MOUNT_HASH, MOUNT_PATH, blockText } from "./mount/words.js";

const MACHINE_HASH = "#/machine";

// What the view was opened with and from where, kept until the page takes them: `open` can run before the page is made.
let asked = null;
let origin = MACHINE_HASH;
let arrive = () => {};

// `preset` holds values by the command's parameter names. Its `device_query` names the device to start with, the way the command reads one.
export function open(_context, { preset }) {
  asked = preset;
  if (location.hash === MOUNT_HASH) return arrive();
  origin = location.hash || "#/";
  location.hash = MOUNT_HASH;
}

// Mount a device, at #/machine/mount: the devices are on screen on arrival, one is chosen, the card beside the list says where it goes and what
// will be asked for, and the mount runs as a task in the Activity panel. Afterwards the page says whether it worked and where the device is.
export function createPart({ activity, tools }) {
  let picture = null;
  let problem = null;
  let picked = "";
  // Values the view was opened with, for the plan of the device that gets chosen, and why the device it was opened for is not chosen.
  let preset = null;
  let note = null;
  let run = null;
  let launching = false;
  let ticket = 0;
  let readAt = 0;
  // A visit that has not seen the devices yet. The one device that can be mounted is chosen for it, so the usual case is a single click.
  let fresh = true;

  const reload = () => keeper.load();
  const list = createDeviceList({
    onRefresh: reload,
    onPick(device) {
      picked = device.path;
      note = null;
      paint();
      // In a narrow window the card sits under the list, out of sight.
      plan.element.scrollIntoView({ block: "nearest", behavior: "smooth" });
    },
  });
  const plan = createPlanCard({ tools, onMount: mount, onRefresh: reload });
  const backLabel = h("span");
  const back = h("a", { class: "mount-back" }, icon("back", 14), backLabel);
  const stamp = h("span", { class: "mount-stamp" });
  const refresh = button({ label: "Refresh", glyph: "refresh", onclick: reload });
  const bannerHolder = h("div");
  const problemHolder = h("div");
  const columns = h("div", { class: "mount-columns" }, list.element, plan.element);
  const element = h(
    "div",
    { class: "mount", hidden: true },
    h(
      "header",
      { class: "view-head" },
      h("div", { class: "view-title" }, back, h("h1", { text: "Mount a device" }), h("p", { text: "Pick a disk or one of its parts, say where it should appear, and mount it." })),
      h("div", { class: "view-actions" }, stamp, button({ label: "Every option", glyph: "sliders", title: "The command's own form, with everything it can do", onclick: () => tools.open(MOUNT_PATH, { plain: true }) }), refresh),
    ),
    bannerHolder,
    problemHolder,
    columns,
  );

  // The device the view was opened for is chosen when it can be mounted. Otherwise the card says why it is not.
  function takeAsked() {
    const given = asked;
    asked = null;
    if (!given || Object.keys(given).length === 0) return;
    preset = given;
    note = null;
    list.showAll();
    const query = typeof given.device_query === "string" ? given.device_query.trim() : "";
    if (query === "") return;
    const wanted = findDevice(picture.devices, query);
    picked = wanted?.state === "ready" ? wanted.path : "";
    if (!wanted) note = { title: `"${query}" is not in the list`, body: "No device attached to this machine goes by that name, or more than one does. Choose one from the list." };
    else if (wanted.state === "mounted") note = { title: `${titleOf(wanted)} is already mounted`, body: `It is at ${wanted.mounted_at}.` };
    else if (wanted.state === "blocked") note = { title: `${titleOf(wanted)} cannot be mounted here`, body: blockText(wanted, picture.system) };
  }

  function settle() {
    if (!picture) return;
    takeAsked();
    if (picture.devices.find((device) => device.path === picked)?.state !== "ready") picked = "";
    const waiting = picture.devices.filter((device) => device.state === "ready");
    if (fresh && picked === "" && !note && waiting.length === 1) picked = waiting[0].path;
    fresh = false;
  }

  function paint() {
    stamp.textContent = picture && readAt ? `Read at ${formatClock(readAt)}` : "";
    bannerHolder.replaceChildren(
      ...(run
        ? [
            mountBanner(run, {
              onReveal: () => activity.reveal(run.id),
              // Letting go of a mount that is still running does not stop it. The page stops waiting, and the list is read again when it ends.
              onDismiss() {
                run = null;
                paint();
              },
            }),
          ]
        : []),
    );
    const unsupported = problem?.status === 501;
    problemHolder.replaceChildren(
      ...(problem
        ? [
            notice({
              glyph: unsupported ? "plug" : "alert", tone: unsupported ? "" : "bad", title: unsupported ? "Mounting is not available on this system" : "The device list could not be read", body: problem.message,
              action: !unsupported && button({ label: "Try again", glyph: "refresh", small: true, onclick: reload }),
            }),
          ]
        : []),
    );
    columns.hidden = problem !== null;
    if (problem) return;
    const device = picture?.devices.find((other) => other.path === picked) ?? null;
    if (picture) list.render({ picture, picked });
    plan.show({ picture, device, preset, note, busy: launching || run?.phase === "mounting" });
    if (device) preset = null;
  }

  // Only the latest reading is shown. The answer is handed back either way, to the mount that asked for it.
  async function read() {
    const mine = (ticket += 1);
    refresh.disabled = true;
    let found = null;
    let failure = null;
    try {
      found = await readPicture();
    } catch (error) {
      failure = error;
    }
    if (mine !== ticket) return found;
    refresh.disabled = false;
    picture = found;
    problem = failure;
    readAt = Date.now() / 1000;
    if (failure) keeper.spoil();
    settle();
    paint();
    return found;
  }

  async function mount(device, planned) {
    if (launching || run?.phase === "mounting") return;
    launching = true;
    paint();
    await runMount({
      activity, device, plan: planned, read,
      onPhase(next) {
        // A mount the person stopped waiting for does not come back when it ends.
        if (run !== next && next.phase !== "mounting") return;
        launching = false;
        run = next;
        paint();
        if (next.phase === "done" && !element.closest("[hidden]")) element.closest(".stage")?.scrollTo({ top: 0, behavior: "smooth" });
      },
    });
    launching = false;
    paint();
  }

  // Every finished task asks the pages to read again. A mount of this page's own reads the list itself when it ends, so that signal is let pass.
  const keeper = staleKeeper(element, () => (run?.phase === "mounting" ? picture : read()));
  arrive = () => {
    fresh = true;
    back.href = origin;
    backLabel.textContent = origin === MACHINE_HASH ? "Machine" : "Back";
    // Devices that are still current are not read again; what the view was opened with is applied to them as they stand.
    if (keeper.ensure() !== false || !picture) return;
    settle();
    paint();
  };
  paint();
  return { element, show: () => arrive() };
}
