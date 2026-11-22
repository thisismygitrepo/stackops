import { h, tildify } from "/assets/scripts/dom.js";
import { api, state } from "/assets/scripts/state.js";
import { createPanel } from "../../live_panel.js";
import { avatar, button, notice } from "../../widgets.js";
import { plural } from "../../words.js";
import { previewList } from "./workbench_kit.js";

const JOBS_FOLDER = ".ai/agents/";
const JOB_PREVIEW = 6;
// The server lists at most this many entries of a folder, so a longer list of jobs, or of one job's agents, stops there.
const LISTING_LIMIT = 40;

const foldersIn = async (prefix) => (await api.paths(prefix, state.settings.workingDirectory)).entries.filter((entry) => entry.endsWith("/"));

// A job is a folder that splitting wrote into this project, with one folder per agent under prompts/.
// A design choice: the list is read from those folders through the path lookup the forms already use, so it needs no command of its own.
// It looks only in the working folder shown at the top of the page, which is where a job lands when that folder is the top of a project.
export function createJobsPanel({ tools }) {
  function row(job) {
    const size = job.agents === 0 ? "Not split yet" : job.agents === LISTING_LIMIT ? `${LISTING_LIMIT} agents or more` : plural(job.agents, "agent");
    const collect = () => tools.open("agents parallel collect", { preset: { agent_dir: job.folder, output_path: `${job.folder}/collected.txt` } });
    return h(
      "li",
      { title: job.folder },
      avatar(job.name, 34),
      h("div", {}, h("strong", { text: job.name }), h("span", { class: "dim", text: size })),
      job.agents > 0 && button({ label: "Join the pieces", glyph: "download", small: true, title: "Puts every agent's share of the list, as the agent left it, back into one file.", onclick: collect }),
    );
  }

  return createPanel({
    title: "Jobs in this project",
    load: async () => {
      const folders = await foldersIn(JOBS_FOLDER);
      return Promise.all(
        folders.map(async (entry) => ({ folder: entry.slice(0, -1), name: entry.slice(JOBS_FOLDER.length, -1), agents: (await foldersIn(`${entry}prompts/`)).filter((share) => /\/agent_[^/]*\/$/.test(share)).length })),
      );
    },
    render: (jobs, { setCount }) => {
      setCount(jobs.length === 0 ? "" : jobs.length === LISTING_LIMIT ? `the first ${LISTING_LIMIT} jobs` : plural(jobs.length, "job"));
      if (jobs.length === 0) {
        return notice({
          glyph: "lanes", title: "No jobs here yet",
          body: `Splitting a job writes it to ${JOBS_FOLDER} at the top of a project, and it then shows up here, ready for its pieces to be joined back into one file. Nothing is there under ${tildify(state.settings.workingDirectory, state.boot.home)}.`,
        });
      }
      return h("div", { class: "wb-models" }, previewList(jobs, JOB_PREVIEW, row));
    },
  });
}
