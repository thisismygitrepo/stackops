import { h } from "/assets/scripts/dom.js";
import { partLoaders } from "../features.js";
import { createParts } from "../space_kit.js";
import { createOverview } from "./settings/overview.js";

// Views that swap in place: the overview at #/settings, and the ones the Settings feature list names (feature_lists/settings.js): the settings
// files, the guided setup, the setup scripts and the packaged files.
export function createSettingsSpace(context) {
  const overview = createOverview(context);
  const element = h("section", { class: "view", hidden: true }, overview.element);
  return { element, show: createParts({ element, built: { "": overview }, loaders: partLoaders("settings"), context }) };
}
