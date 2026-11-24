import { h, icon } from "/assets/scripts/dom.js";
import { button, glyphTile, pathChip } from "../../../widgets.js";
import { formPreset, planOf, startingChoice, titleOf } from "./model.js";
import { createMore } from "./plan_more.js";
import { createWhere } from "./plan_place.js";
import { MOUNT_PATH, READ_ONLY_OFF, STATES, asksLine, fileSystemName, isStuck, sizeText } from "./words.js";

const STEPS = ["Choose a device from the list", "Say where it should appear", "Mount it"];
const NAME_LIMIT = 22;

// What the card shows while no device is chosen: the three steps, under a line that says where things stand.
function idle({ picture, note }) {
  const waiting = picture ? picture.devices.filter((device) => device.state === "ready").length : 0;
  const stuck = picture ? picture.devices.filter(isStuck).length : 0;
  const lead = !picture
    ? ["Looking for devices…", "Reading what is attached to this machine."]
    : note
      ? [note.title, note.body]
      : waiting > 0
        ? ["Choose a device", "Pick one from the list. The choices for it show up here."]
        : stuck > 0
          ? ["Nothing can be mounted yet", `${stuck === 1 ? "One device needs" : `${stuck} devices need`} something first. The list says what.`]
          : ["No device chosen", "Once something can be mounted, choose it in the list. The choices for it show up here."];
  return h(
    "div",
    { class: "mount-idle" },
    h("span", { class: "mount-idle-glyph" }, icon("plug", 26)),
    h("h2", { text: lead[0] }),
    h("p", { text: lead[1] }),
    h("ol", { class: "mount-steps" }, STEPS.map((text, index) => h("li", {}, h("b", { class: "mount-step", text: String(index + 1) }), h("span", { text })))),
  );
}

// The plan for one device: where it goes, read-only or not, the rest under "More options", what will be asked for, and the button.
// The choices live here and start afresh for every device. `onMount(device, plan)` is called with the plan as it stands at the click.
function build({ picture, device, preset, tools, onMount }) {
  const { system } = picture;
  const choice = startingChoice(picture, device, preset);
  const name = titleOf(device);
  let busy = false;
  const current = () => planOf(picture, device, choice);
  const ask = h("p", { class: "mount-ask" });
  const problem = h("p", { class: "mount-problem" });
  const go = button({ label: name.length <= NAME_LIMIT ? `Mount ${name}` : "Mount this device", glyph: "plug", tone: "primary", onclick: () => onMount(device, current()) });
  const readOnlyHint = h("span", { class: "field-hint" });
  const readOnly = h(
    "button",
    {
      class: "field toggle-row mount-read-only", type: "button", role: "switch",
      onclick: () => {
        choice.readOnly = !choice.readOnly;
        paint();
      },
    },
    h("div", {}, h("span", { class: "field-label" }, h("span", { text: "Read-only" })), readOnlyHint),
    h("i", { class: "switch" }),
  );
  const where = createWhere({ picture, device, choice, changed: paint });
  const more = createMore({ picture, device, choice, changed: paint, openForm: () => tools.open(MOUNT_PATH, { plain: true, preset: formPreset(device, current()) }) });

  function paint() {
    const plan = current();
    where.paint(plan);
    more.paint(plan);
    readOnly.disabled = !plan.way.read_only;
    readOnly.setAttribute("aria-checked", String(plan.readOnly));
    readOnlyHint.textContent = plan.way.read_only ? "Nothing on the device can be changed while it is mounted." : READ_ONLY_OFF[system];
    const line = asksLine({ asks: plan.asks, withKey: plan.withKey, system, elevated: picture.elevated });
    ask.className = `mount-ask${line.lock ? " lock" : ""}`;
    ask.replaceChildren(icon(line.lock ? "lock" : "check", 15), h("span", { text: line.text }));
    problem.textContent = busy ? "" : (plan.problems[0] ?? "");
    go.disabled = busy || plan.problems.length > 0;
  }

  const element = h(
    "div",
    { class: "mount-plan-body" },
    h(
      "header",
      { class: "mount-plan-head" },
      glyphTile(device.encryption ? "lock" : device.kind === "disk" ? "server" : "database", STATES.ready.hue, 46),
      h("div", {}, h("h2", { text: name }), h("p", { text: [sizeText(device), fileSystemName(device)].filter(Boolean).join(" · ") }), pathChip(device.path)),
    ),
    h("section", { class: "mount-plan-part" }, h("h3", {}, h("b", { class: "mount-step", text: "2" }), "Where it should appear"), where.element, readOnly, more.element),
    h("section", { class: "mount-plan-part" }, h("h3", {}, h("b", { class: "mount-step", text: "3" }), "Mount it"), ask, go, problem),
  );
  paint();
  return {
    element,
    setBusy(next) {
      busy = next;
      paint();
    },
  };
}

// The card beside the list. It keeps a device's choices while the list is read again, and starts over when another device is chosen, when the
// device itself changed, or when the view is opened with values for it.
export function createPlanCard({ tools, onMount }) {
  const element = h("aside", { class: "mount-card mount-plan" });
  let built = null;
  return {
    element,
    show({ picture, device, preset, note, busy }) {
      if (!device) {
        built = null;
        element.replaceChildren(idle({ picture, note }));
        return;
      }
      const signature = JSON.stringify([picture.system, picture.elevated, picture.letters, device]);
      if (built?.signature !== signature || preset) {
        built = { signature, ...build({ picture, device, preset: preset ?? {}, tools, onMount }) };
        element.replaceChildren(built.element);
      }
      built.setBusy(busy);
    },
  };
}
