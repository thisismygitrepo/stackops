import { h } from "/assets/scripts/dom.js";
import { createLivePanel } from "../../live_panel.js";
import { toolButton } from "../../space_kit.js";
import { button, copyChip, keyValue, pill } from "../../widgets.js";
import { formatBytes, plural, relativeTime } from "../../words.js";
import { actionBlock, areaHead, installButton, isRunning, previewList, reloadAfterStart, stateCard, statusPill } from "./workbench_kit.js";
import { createCatalogPanel } from "./workbench_local_catalog.js";

const DOCTOR = "agents local doctor";
const SERVE = "agents local serve";
const MODEL_PREVIEW = 6;
const ACTIONS = [
  { path: SERVE, blurb: "Serve one model fast enough for several agents at once. Needs vLLM." },
  { path: "agents local install", blurb: "Set up vLLM, the fast model server, for this machine's graphics hardware." },
  { path: DOCTOR, title: "Check a server elsewhere", blurb: "Look at a model server on another machine or at another address." },
];

function modelList(rows) {
  const line = (row) => h("li", { title: row.title }, h("div", {}, h("strong", { text: row.name }), h("span", { class: "dim", text: row.detail })), row.trail);
  return h("div", { class: "wb-models" }, previewList(rows, MODEL_PREVIEW, line));
}

const running = (data) => h("div", { class: "wb-server-head" }, statusPill("Running", "good", "check"), copyChip(data.host), data.errors.length > 0 && h("span", { class: "dim", text: "Some details couldn't be read just now." }));

export function createLocalArea({ activity, tools }, { setStatus }) {
  const seen = {};
  function report(name, up, installed) {
    seen[name] = { up, installed };
    const servers = Object.entries(seen);
    const live = servers.filter(([, server]) => server.up).map(([label]) => label);
    if (live.length) setStatus(live.length === 1 ? `${live[0]} running` : `${live.length} servers running`, "good");
    else setStatus(servers.some(([, server]) => server.installed) ? "Nothing running" : "Not set up", "");
  }

  const ollama = createLivePanel({
    title: "Ollama", path: DOCTOR, extra: ["--backend", "ollama", "--json"], locked: ["backend", "api_key"],
    render: (data, { setCount, reload }) => {
      const up = data.version !== null || data.models !== null;
      report("Ollama", up, Boolean(data.cli_path));
      setCount(data.version ? `version ${data.version}` : "");
      if (!up && !data.cli_path) {
        return stateCard({
          glyph: "download", title: "Ollama isn't installed", body: "The easiest way to run open models here: it downloads a model and has it answering within minutes.",
          actions: [installButton(tools, "ollama", "Install Ollama")],
        });
      }
      if (!up) {
        return stateCard({
          glyph: "power", title: "Ollama is installed, but not running", body: "Open the Ollama app and its models will show up here.",
          actions: [button({ label: "Check again", glyph: "refresh", onclick: reload })],
        });
      }
      const models = data.models ?? [];
      const loaded = new Map((data.running_models ?? []).map((model) => [model.name, model]));
      const rows = models.map((model) => {
        const live = loaded.get(model.name);
        return {
          name: model.name,
          detail: model.remote ? "Runs in the cloud" : [model.parameter_size, model.quantization_level, formatBytes(model.size)].filter(Boolean).join(" · "),
          title: live ? `Using ${formatBytes(live.size_vram)} of graphics memory · unloads ${relativeTime(live.expires_at)}` : undefined,
          trail: live ? pill("In memory", "accent") : h("span", { class: "dim", text: relativeTime(model.modified_at) }),
        };
      });
      rows.sort((first, second) => Number(loaded.has(second.name)) - Number(loaded.has(first.name)));
      return h(
        "div",
        { class: "stack" },
        running(data),
        models.length === 0
          ? h("p", { class: "wb-note", text: "No models are downloaded yet. Pick one from the list below." })
          : h("span", { class: "stat-label", text: `${plural(models.length, "model")} · ${formatBytes(models.reduce((total, model) => total + model.size, 0))} on disk · ${loaded.size} in memory` }),
        models.length > 0 && modelList(rows),
      );
    },
  });

  const vllm = createLivePanel({
    title: "vLLM", path: DOCTOR, extra: ["--backend", "vllm", "--json"], locked: ["backend"],
    render: (data, { setCount, reload }) => {
      report("vLLM", data.healthy, Boolean(data.cli_path));
      setCount(data.version ? `version ${data.version}` : "");
      if (!data.healthy && !data.cli_path) {
        return stateCard({
          glyph: "download", title: "vLLM isn't installed", body: "A faster server for when several agents share one model. It needs a capable graphics card or Apple Silicon.",
          actions: [toolButton(tools, "agents local install", { label: "Install vLLM", glyph: "download", tone: "primary" })],
        });
      }
      // A server takes minutes to load its model, far longer than the one look after its start waits, so a start from this page is said in words.
      if (!data.healthy && isRunning(activity, SERVE)) {
        return stateCard({
          glyph: "clock", title: "A model server was started from here", body: "It is not answering at this address yet. Loading a model can take a few minutes.",
          actions: [button({ label: "Check again", glyph: "refresh", onclick: reload })],
        });
      }
      if (!data.healthy) {
        return stateCard({
          glyph: "power", title: "vLLM is installed, but no server is running", body: "Start one with the model you want agents to use.",
          actions: [toolButton(tools, SERVE, { label: "Start a model server", glyph: "play", tone: "primary" })],
        });
      }
      const percent = (share) => (share === null || share === undefined ? null : `${Math.round(share * 100)}%`);
      return h(
        "div",
        { class: "stack" },
        running(data),
        modelList((data.models ?? []).map((model) => ({ name: model.name, detail: model.max_model_len ? `Reads up to ${model.max_model_len.toLocaleString()} tokens at once` : "Being served", trail: pill("Serving", "accent") }))),
        data.metrics && keyValue([["Answering now", data.metrics.running_requests], ["Waiting in line", data.metrics.waiting_requests], ["Busiest memory use", percent(data.metrics.peak_kv_cache_usage)]]),
      );
    },
  });

  reloadAfterStart(activity, SERVE, vllm);

  const catalog = createCatalogPanel({ tools });
  const element = h(
    "div",
    { class: "wb-area" },
    areaHead({
      title: "Local models", lede: "Run AI models on this machine instead of a cloud service, so nothing you ask leaves your computer.",
      actions: [toolButton(tools, SERVE, { label: "Start a model server", glyph: "play", tone: "primary" })],
    }),
    h("div", { class: "wb-pair" }, ollama.element, vllm.element),
    actionBlock(tools, "Run and install", ACTIONS),
    catalog.element,
  );
  return {
    element,
    show() {
      ollama.ensure();
      vllm.ensure();
      catalog.ensure();
    },
  };
}
