import { h } from "/assets/scripts/dom.js";
import { copyChip } from "../../../widgets.js";
import { plural } from "../../../words.js";
import { RESTART_LEDE, dirtyCount, home, pushCount, remoteName } from "./words.js";

// What to do once an update has run, with the command that starts this web UI again the way it was started.
export function restartSteps(state) {
  return h(
    "ol",
    { class: "machine-update-restart" },
    h("li", {}, "Go to the terminal the web UI was started from and press ", h("kbd", { text: "Ctrl" }), " ", h("kbd", { text: "C" }), "."),
    h("li", {}, "Start it again with ", copyChip(state.restart_command)),
    h("li", { text: "Open the link it prints. The link you are on now stops working, because every start makes a new one." }),
  );
}

// What "Commit and push my changes first" does to the source folder as it is right now, in the order it does it.
export function developerEffects(state) {
  const { checkout } = state;
  const dirty = dirtyCount(checkout);
  const pushed = pushCount(checkout);
  const where = `${remoteName(checkout.origin)}, branch ${checkout.branch}`;
  return [
    dirty > 0 ? `Commits ${plural(dirty, "file")} in one commit called "${state.commit_message}". That is ${plural(checkout.changed, "changed file")} and ${plural(checkout.untracked, "new file")}, everything git does not ignore.` : "Finds nothing to commit, as the folder is now.",
    `Pulls from ${checkout.upstream || "the branch it follows"} and puts your commits on top of what comes in.`,
    pushed > 0 ? `Pushes ${plural(pushed, "commit")} to ${where}. Everyone who can see that repository sees ${pushed === 1 ? "it" : "them"}, and this page cannot take ${pushed === 1 ? "it" : "them"} back.` : `Pushes to ${where}, where there is nothing new of yours to send.`,
  ];
}

// The update's steps in the order the command runs them, for the options as they are set now. The last one is the person's own.
export function stepsOf(state, effects, options) {
  const folder = state.checkout ? home(state.checkout.path) : "";
  const steps = [];
  if (state.route === "checkout" && options.developer) {
    steps.push({ tone: "bad", title: "Commit your changes, pull, and push", detail: developerEffects(state).join(" ") });
  } else if (state.route === "checkout") {
    steps.push({ tone: "", title: "Pull the source folder", detail: `Brings ${folder} up to ${state.checkout.upstream || "the branch it follows"}. It only moves forward, and stops here if it cannot.` });
  }
  steps.push({ tone: "", title: "Update uv", detail: "uv is the installer StackOps is installed with. It updates itself first." });
  steps.push(
    state.route === "checkout"
      ? { tone: "", title: "Install StackOps again from the source folder", detail: `Rebuilds the tool from ${folder} with Python ${state.python}, and brings the packages it uses up to date.` }
      : { tone: "", title: "Install the newest release", detail: `Downloads the newest StackOps from PyPI and installs it with Python ${state.python}, together with the packages it uses.` },
  );
  if (options.refresh) steps.push({ tone: "", title: "Refresh StackOps's scripts and settings", detail: `Copies them into ${effects ? home(effects.config_folder) : "its settings folder"}, over the old copies.` });
  if (options.settings) {
    const present = effects?.settings?.present.length;
    steps.push({ tone: "warn", title: "Replace your app settings", detail: present === undefined ? "Deletes your own settings files and puts the packaged ones in their place." : `Deletes your settings for ${plural(present, "program")} and puts the packaged ones in their place.` });
  }
  if (options.shell) {
    const shell = effects?.shell;
    steps.push({ tone: "", title: "Set up the shell's startup file", detail: !shell ? "Adds the line that loads StackOps, if it is missing." : shell.loaded ? `${home(shell.profile)} already loads StackOps, so nothing changes.` : `Adds one line to ${home(shell.profile)}.` });
  }
  steps.push({ tone: "you", title: "Then you restart the web UI", detail: RESTART_LEDE, extra: restartSteps(state) });
  return steps;
}
