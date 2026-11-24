import { plural, relativeTime } from "../../../words.js";
import { dirtyCount, home, incomingCount, isWindowsTool } from "./words.js";

const when = (value) => relativeTime(value) || "some time ago";

// Why the update cannot work from here as things stand, with the way forward, or null when nothing is in its way. Each of these is a case where
// the command would stop at its first step, so the page says so in place of letting it fail in the console.
export function blockerOf(state, latest, options) {
  if (isWindowsTool(state)) {
    return { title: "Windows cannot replace StackOps while it is running", body: "This web UI is StackOps running, so the update cannot finish from here. Stop the web UI, then run this in a terminal.", command: "devops self update" };
  }
  if (state.route !== "checkout") return null;
  const { checkout } = state;
  const folder = home(checkout.path);
  if (checkout.problem === "not_repository") {
    return { title: "The source folder has no git history", body: `The update pulls ${folder} with git before it installs from it, and git does not know that folder. Clone StackOps there again, or move the folder away to update from PyPI.` };
  }
  if (checkout.problem === "unreadable") return { title: "Git could not read the source folder", body: `Open a terminal in ${folder} and run this to see what is wrong, then check again.`, command: "git status" };
  if (checkout.unfinished) return { title: `A ${checkout.unfinished} is waiting to be finished`, body: `Git will not pull into ${folder} until the ${checkout.unfinished} there is finished or cancelled.` };
  if (checkout.branch === "") return { title: "No branch is checked out", body: `${folder} sits on a single commit, so git has no branch to bring up to date. Check out a branch there first.` };
  if (checkout.upstream === "") return { title: `The branch ${checkout.branch} follows nothing`, body: "The update pulls from the branch this one follows, and none is set. Set one in a terminal, then check again.", command: `git branch --set-upstream-to origin/${checkout.branch}` };
  const incoming = incomingCount(checkout, latest);
  if (!options.developer && checkout.ahead > 0 && incoming > 0) {
    return {
      title: "Your commits and the ones waiting have gone separate ways",
      body: `You have ${plural(checkout.ahead, "commit")} that ${checkout.ahead === 1 ? "is" : "are"} not pushed, and ${plural(incoming, "new commit")} ${incoming === 1 ? "is" : "are"} waiting. A plain update only moves the folder forward, so it would stop at its first step. Turn on "Commit and push my changes first" below, which puts your commits on top of the new ones, or sort it out in a terminal.`,
    };
  }
  return null;
}

// A remark that does not stop the update but that the person should have read before starting it.
export function cautionOf(state, latest, options) {
  // The update always works on uv's tool. A copy installed some other way is not that tool, and stays as it is.
  if (state.installed === null) return "StackOps runs here from its source files. The update installs it as a uv tool and leaves these files alone.";
  if (!state.installed.uv_tool) return `This copy is not one of uv's tools. The update installs StackOps as a uv tool next to it, and this copy stays at ${state.installed.version}.`;
  // The command decides where to install from by whether a source folder is in its usual place, not by where the tool came from last time.
  if (!state.same_source) {
    const before = state.installed.source === "index" ? "PyPI" : home(state.installed.origin);
    return state.route === "checkout"
      ? `The tool was installed from ${before}. A source folder exists at ${home(state.checkout.path)}, so the update installs from that folder in its place.`
      : `The tool was installed from ${before}. The update puts the newest release from PyPI in its place.`;
  }
  if (state.route !== "checkout" || state.checkout.problem !== "" || options.developer) return "";
  if (dirtyCount(state.checkout) > 0 && incomingCount(state.checkout, latest) > 0) return "You have changes that are not committed. If a waiting commit touches the same files, the pull stops and nothing is updated.";
  return "";
}

function fromLastFetch(state, lead) {
  const { checkout } = state;
  const fetched = checkout.fetched_at === null ? "It has never fetched." : `It last fetched ${when(checkout.fetched_at)}.`;
  if (checkout.behind > 0) {
    return { tone: "accent", pill: "Update available", title: `${plural(checkout.behind, "commit")} waiting, as of the last fetch`, detail: `${lead} ${fetched} The update fetches again by itself.`, target: "", available: true };
  }
  return { tone: "", pill: "Not checked", title: "Nothing was waiting at the last fetch", detail: `${lead} ${fetched} The update fetches again by itself, so it may still find something new.`, target: "", available: false };
}

// Why there is no answer: the network, the site, or this web UI's own server, which can be older than the page it serves.
const TROUBLE = {
  offline: (site) => `${site} did not answer, so the network may be down.`,
  refused: (site) => `${site} turned the question down just now.`,
  server: (site) => `The StackOps server could not ask ${site}.`,
};

function releaseVerdict(state, latest) {
  const mine = state.installed?.version ?? state.started_version;
  if (latest.trouble) {
    return { tone: "", pill: "Not checked", title: "Could not look for a newer release", detail: `${TROUBLE[latest.trouble]("PyPI")} You can still update. It installs whatever is newest once PyPI answers.`, target: "", available: false };
  }
  if (latest.standing === "outdated") {
    const between = latest.releases.length > 1 ? ` ${plural(latest.releases.length, "release")}${latest.more ? " or more" : ""} came out since.` : "";
    return { tone: "accent", pill: "Update available", title: `Version ${latest.version} is out`, detail: `You have ${mine}.${between} The newest came out ${when(latest.released_at)}.`, target: latest.version, available: true };
  }
  if (latest.standing === "ahead") {
    return { tone: "", pill: "Ahead", title: "You are ahead of the newest release", detail: `You have ${mine} and the newest release is ${latest.version}. An update would not bring a newer StackOps.`, target: "", available: false, settled: true };
  }
  if (latest.standing === "current") return { tone: "good", pill: "Up to date", title: "You have the newest release", detail: `${latest.version} came out ${when(latest.released_at)}, and nothing newer is out.`, target: "", available: false, settled: true };
  return { tone: "", pill: "Cannot compare", title: `The newest release is ${latest.version}`, detail: "The version installed here could not be read, so the page cannot say which is newer.", target: "", available: false };
}

function commitVerdict(state, latest) {
  const { checkout } = state;
  if (latest.source === "none") return fromLastFetch(state, `The branch ${checkout.branch} does not follow one on GitHub, so this is what ${home(checkout.path)} knew when it last asked.`);
  if (latest.trouble) return fromLastFetch(state, `${TROUBLE[latest.trouble]("GitHub")} This is what ${home(checkout.path)} knew when it last asked.`);
  const mine = state.installed?.version ?? state.started_version;
  const count = latest.commits.length;
  if (count > 0) {
    const bump = latest.version && latest.version !== mine ? ` They take StackOps from ${mine} to ${latest.version}.` : "";
    return {
      tone: "accent", pill: "Update available", title: `${plural(count, "new commit")}${latest.more ? " or more" : ""} on GitHub`,
      detail: `${home(checkout.path)} does not have ${count === 1 ? "it" : "them"} yet.${bump}`, target: latest.version && latest.version !== mine ? latest.version : "", available: true,
    };
  }
  const own = checkout.ahead > 0 ? ` ${plural(checkout.ahead, "commit")} of yours ${checkout.ahead === 1 ? "is" : "are"} not pushed yet.` : "";
  return { tone: "good", pill: "Up to date", title: "Your source folder has everything GitHub has", detail: `Nothing new on ${checkout.online_branch} since the commit you are on.${own}`, target: "", available: false, settled: true };
}

// What the top of the page says: how this machine stands against the newest version there is. `latest` is null while the network is still asked.
// `available` says there is something to get, and `settled` that there is known to be nothing.
export function verdictOf(state, latest) {
  const { checkout } = state;
  // A source folder that is on no branch, or on one that follows nothing, has nothing to be compared with.
  if (state.route === "checkout" && (checkout.problem !== "" || checkout.branch === "" || checkout.upstream === "")) {
    return { tone: "", pill: "Not checked", title: "The source folder is not ready for an update", detail: "What is in the way is under this, with what to do about it.", target: "", available: false };
  }
  if (latest === null) {
    const asking = state.route === "index" ? "Asking PyPI which release is the newest." : checkout.online ? "Asking GitHub which commits your source folder does not have yet." : "Reading what your source folder knows about the branch it follows.";
    return { tone: "", pill: "Checking", title: "Looking for a newer version", detail: asking, target: "", available: false, busy: true };
  }
  return state.route === "index" ? releaseVerdict(state, latest) : commitVerdict(state, latest);
}
