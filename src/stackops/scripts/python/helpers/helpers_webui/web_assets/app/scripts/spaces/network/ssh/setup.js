import { h, icon, toast } from "/assets/scripts/dom.js";
import { confirmAction } from "../../../overlays.js";
import { button, pill, skeleton } from "../../../widgets.js";
import { card, cardHead, reason, stepList } from "../kit.js";
import { PATHS } from "../words.js";
import { serviceState } from "./checks.js";

const lowered = (text) => text.charAt(0).toLowerCase() + text.slice(1);

// What "set up" would do on this machine, shown before it runs: what it installs, each step, who has to approve it and the exact script.
// The plan is read from the script the command runs; the command itself is started only from the button, as a task to watch.
export function createSetupCard({ activity }) {
  const state = h("span");
  const body = h("div", { class: "network-setup-body" }, skeleton(3, "row"));
  let starting = false;

  async function run(plan) {
    if (starting) return;
    const agreed = await confirmAction({
      title: "Set up SSH access on this machine?",
      body: `This will ${plan.steps.map((step) => lowered(step.title)).join(", then ")}. ${plan.password.startsWith("Nothing") ? "" : `It asks for ${lowered(plan.password)} `}Once it is on, anyone with an allowed key, or this account's password where passwords are accepted, can sign in from the network.`,
      confirm: "Set it up",
    });
    if (!agreed) return;
    starting = true;
    try {
      // Interactive, so the password can be typed where the command asks for it. Every page reads this machine again when the run ends.
      await activity.start({ title: "Set up SSH access", emoji: "📡", arguments: PATHS.setup.split(" "), interactive: true, reveal: true });
    } catch (error) {
      toast(error.message);
    } finally {
      starting = false;
    }
  }

  function paint({ plan, checks }) {
    if (plan.blocker) {
      state.replaceChildren(pill("Not available here", ""));
      body.replaceChildren(reason(plan.blocker), h("div", { class: "network-card-actions" }, h("button", { class: "btn primary", type: "button", disabled: true }, icon("power", 16), h("span", { text: "Set up SSH access" }))));
      return;
    }
    // Nothing is claimed that the checks did not say: before they arrive, and when the one about the service could not be read.
    const standing = checks === null ? "" : serviceState(checks);
    const on = standing === "on";
    state.replaceChildren(...(standing === "" ? [] : [on ? pill("Already on", "good") : standing === "off" ? pill("Not on yet", "warn") : pill("Could not tell if it is on", "")]));
    body.replaceChildren(
      h("p", { class: "network-setup-lede", text: on ? `SSH is already switched on, so running this again changes nothing on ${plan.system}. This is what it does:` : `This is what setting up does on ${plan.system}, in order:` }),
      stepList(plan.steps),
      h("dl", { class: "facts network-setup-facts" }, h("dt", { text: "Installs" }), h("dd", { text: plan.installs }), h("dt", { text: "Asks for" }), h("dd", { text: plan.password })),
      ...plan.notes.map(reason),
      h("details", { class: "fold" }, h("summary", {}, icon("chevron", 13), h("span", { text: "The exact script it runs" })), h("pre", { class: "output network-setup-script", text: plan.script })),
      h("div", { class: "network-card-actions" }, button({ label: on ? "Run it anyway" : "Set up SSH access", glyph: "power", tone: on ? "plain" : "primary", onclick: () => run(plan) })),
    );
  }

  return { element: card({ class: "network-ssh-setup" }, cardHead("Switch SSH on", state), body), paint };
}
