const SVG_NAMESPACE = "http://www.w3.org/2000/svg";

const ICONS = {
  home: '<path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
  dashboard: '<rect x="3" y="3" width="8" height="10" rx="1.5"/><rect x="13" y="3" width="8" height="6" rx="1.5"/><rect x="13" y="11" width="8" height="10" rx="1.5"/><rect x="3" y="15" width="8" height="6" rx="1.5"/>',
  map: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3.5"/><path d="M12 3v5.5M12 15.5V21M3 12h5.5M15.5 12H21"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
  play: '<path d="M7 4.5v15l12-7.5z"/>',
  stop: '<rect x="6" y="6" width="12" height="12" rx="2"/>',
  close: '<path d="M6 6l12 12M18 6 6 18"/>',
  chevron: '<path d="m9 6 6 6-6 6"/>',
  down: '<path d="m6 9 6 6 6-6"/>',
  up: '<path d="m6 15 6-6 6 6"/>',
  copy: '<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>',
  refresh: '<path d="M20 11A8 8 0 0 0 6.3 6.3L4 8.5M4 4v4.5h4.5M4 13a8 8 0 0 0 13.7 4.7L20 15.5M20 20v-4.5h-4.5"/>',
  expand: '<path d="M8 3H5a2 2 0 0 0-2 2v3M16 3h3a2 2 0 0 1 2 2v3M8 21H5a2 2 0 0 1-2-2v-3M16 21h3a2 2 0 0 0 2-2v-3"/>',
  shrink: '<path d="M8 3v3a2 2 0 0 1-2 2H3M21 8h-3a2 2 0 0 1-2-2V3M3 16h3a2 2 0 0 1 2 2v3M16 21v-3a2 2 0 0 1 2-2h3"/>',
  folder: '<path d="M3 6a2 2 0 0 1 2-2h4l2 3h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
  terminal: '<path d="m5 17 6-5-6-5M13 18h7"/>',
  check: '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
  alert: '<path d="M12 4 2.5 20h19zM12 10v4.5M12 17.4v.2"/>',
  report: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8zM14 3v5h5M9 13h6M9 17h6"/>',
  arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
};

export function h(tag, properties = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(properties)) {
    if (value === undefined || value === null || value === false) continue;
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (key === "value") node.value = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value === true ? "" : value);
  }
  node.append(...children.flat().filter((child) => child !== null && child !== undefined && child !== false));
  return node;
}

export function icon(name, size = 16) {
  const svg = document.createElementNS(SVG_NAMESPACE, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("width", size);
  svg.setAttribute("height", size);
  svg.setAttribute("aria-hidden", "true");
  svg.classList.add("icon");
  svg.innerHTML = ICONS[name];
  return svg;
}

export function shellQuote(token) {
  return /^[\w@%+=:,./-]+$/.test(token) ? token : `'${token.replaceAll("'", `'\\''`)}'`;
}

export function splitArguments(text) {
  const tokens = [];
  let current = "";
  let started = false;
  let quote = null;
  for (let index = 0; index < text.length; index += 1) {
    const character = text[index];
    if (quote === "'") {
      if (character === "'") quote = null;
      else current += character;
    } else if (quote === '"') {
      if (character === '"') quote = null;
      else if (character === "\\" && index + 1 < text.length && '"\\$`'.includes(text[index + 1])) current += text[(index += 1)];
      else current += character;
    } else if (character === "'" || character === '"') {
      quote = character;
      started = true;
    } else if (character === "\\" && index + 1 < text.length) {
      current += text[(index += 1)];
      started = true;
    } else if (/\s/.test(character)) {
      if (started) tokens.push(current);
      current = "";
      started = false;
    } else {
      current += character;
      started = true;
    }
  }
  if (started) tokens.push(current);
  return tokens;
}

export function formatDuration(seconds) {
  if (seconds < 60) return `${seconds < 10 ? seconds.toFixed(1) : Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
  return `${Math.floor(seconds / 3600)}h ${Math.round((seconds % 3600) / 60)}m`;
}

export function formatClock(epochSeconds) {
  return new Date(epochSeconds * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function tildify(path, home) {
  return path === home ? "~" : path.startsWith(`${home}/`) ? `~${path.slice(home.length)}` : path;
}

export function debounce(callback, milliseconds) {
  let timer = 0;
  return (...parameters) => {
    clearTimeout(timer);
    timer = setTimeout(() => callback(...parameters), milliseconds);
  };
}

const toasts = h("div", { class: "toasts", role: "status" });

export function toast(message, tone = "error") {
  if (!toasts.isConnected) document.body.append(toasts);
  const note = h("div", { class: `toast ${tone}` }, h("span", { text: message }));
  toasts.append(note);
  setTimeout(() => note.remove(), tone === "error" ? 9000 : 4000);
}
