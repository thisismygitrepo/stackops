import { h, icon } from "/assets/scripts/dom.js";
import { createLivePanel } from "../../live_panel.js";
import { rise } from "../../motion.js";
import { avatar, button, copyChip, notice, pill } from "../../widgets.js";
import { humanize, plural, relativeTime } from "../../words.js";
import { cardHead, compact } from "./workbench_kit.js";

const outside = (href, label) => h("a", { class: "link wb-outside", href, target: "_blank", rel: "noopener noreferrer" }, h("span", { text: label }), icon("external", 12));
const gigabytes = (size) => (size ? (size.minimum_gb === size.maximum_gb ? `${size.minimum_gb} GB` : `${size.minimum_gb}–${size.maximum_gb} GB`) : "");

// The catalog answers with Ollama model families, or with single Hugging Face models when the vLLM catalog is chosen under Options.
function ollamaCard(model) {
  return h(
    "article",
    { class: "wb-card lit" },
    cardHead(avatar(model.name, 40), model.name, `${model.pulls} downloads · updated ${model.updated}`),
    h("p", { class: "wb-clamp", title: model.description, text: model.description }),
    h(
      "div",
      { class: "wb-sizes", title: "Copy the name to ask Ollama for this size" },
      model.sizes.map((size) => copyChip(`${model.name}:${size}`, [size.toUpperCase(), gigabytes(model.download_sizes_gb?.[size])].filter(Boolean).join(" · "))),
    ),
    h("footer", {}, h("div", { class: "chip-row" }, model.capabilities.map((capability) => pill(humanize(capability)))), outside(`https://ollama.com/library/${encodeURIComponent(model.name)}`, "ollama.com")),
  );
}

function huggingFaceCard(model, tools) {
  const [owner, name] = model.name.includes("/") ? model.name.split("/") : ["", model.name];
  return h(
    "article",
    { class: "wb-card lit" },
    cardHead(avatar(owner || name, 40), name, owner),
    h("div", { class: "chip-row" }, pill(`${(model.parameters / 1e9).toFixed(1)} billion parameters`), model.task && pill(humanize(model.task))),
    h("span", { class: "dim", text: `${compact(model.downloads)} downloads · updated ${relativeTime(model.updated)}` }),
    h(
      "footer",
      {},
      outside(`https://huggingface.co/${model.name}`, "huggingface.co"),
      button({ label: "Serve it", glyph: "play", small: true, onclick: () => tools.open("agents local serve", { preset: { model: model.name } }) }),
    ),
  );
}

export function createCatalogPanel({ tools }) {
  return createLivePanel({
    title: "Models you can download", path: "agents local discover", extra: ["--json"], skeletonShape: "card",
    render: (data, { setCount }) => {
      const models = Array.isArray(data) ? data : [];
      setCount(models.length ? `${plural(models.length, "model")} · fetched live` : "");
      if (models.length === 0) return notice({ glyph: "search", title: "Nothing matches", body: "Try a wider size range or another search under Options." });
      return rise(h("div", { class: "card-grid" }, models.map((model) => ("parameters" in model ? huggingFaceCard(model, tools) : ollamaCard(model)))));
    },
  });
}
