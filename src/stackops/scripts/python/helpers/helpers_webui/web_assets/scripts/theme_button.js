import { h, icon } from "./dom.js";
import { currentTheme, onThemeChange, toggleTheme } from "./theme.js";

// One button for both views. It shows the look a press switches to; each view places it and styles it under its own class name.
export function createThemeButton(className, iconSize) {
  const element = h("button", { class: className, type: "button", onclick: toggleTheme });
  const show = (theme) => {
    const next = theme === "dark" ? "light" : "dark";
    element.replaceChildren(icon(next === "dark" ? "moon" : "sun", iconSize));
    element.title = `Switch to ${next} mode`;
    element.setAttribute("aria-label", element.title);
  };
  onThemeChange(show);
  show(currentTheme());
  return element;
}
