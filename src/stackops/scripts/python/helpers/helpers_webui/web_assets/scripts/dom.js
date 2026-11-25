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
  eject: '<path d="M12 5 4.5 14h15zM5 19h14"/>',
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
  apps: '<rect x="3" y="3" width="7.5" height="7.5" rx="2"/><rect x="13.5" y="3" width="7.5" height="7.5" rx="2"/><rect x="3" y="13.5" width="7.5" height="7.5" rx="2"/><rect x="13.5" y="13.5" width="7.5" height="7.5" rx="2"/>',
  branch: '<circle cx="6" cy="5" r="2.5"/><circle cx="6" cy="19" r="2.5"/><circle cx="18" cy="8" r="2.5"/><path d="M6 7.5v9M18 10.5a6 6 0 0 1-6 6H8.5"/>',
  layers: '<path d="m12 3 9 4.5-9 4.5-9-4.5zM3 12l9 4.5 9-4.5M3 16.5 12 21l9-4.5"/>',
  bot: '<rect x="4" y="8" width="16" height="12" rx="3"/><path d="M12 4.5V8M9 13v2M15 13v2M2 14h2M20 14h2"/><circle cx="12" cy="3.5" r="1"/>',
  sliders: '<path d="M4 6h9M19 6h1M4 12h3M13 12h7M4 18h11"/><circle cx="16" cy="6" r="2.2"/><circle cx="10" cy="12" r="2.2"/><circle cx="18" cy="18" r="2.2"/>',
  globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
  cpu: '<rect x="6" y="6" width="12" height="12" rx="2.5"/><rect x="9.5" y="9.5" width="5" height="5" rx="1"/><path d="M9 3v3M15 3v3M9 18v3M15 18v3M3 9h3M3 15h3M18 9h3M18 15h3"/>',
  chart: '<path d="M4 4v16h16M8.5 16v-4M12.5 16V8M16.5 16v-6"/>',
  cube: '<path d="m3 7.5 9-4.5 9 4.5v9L12 21l-9-4.5zM3 7.5l9 4.5 9-4.5M12 12v9"/>',
  sparkle: '<path d="m11 3 1.9 5.1L18 10l-5.1 1.9L11 17l-1.9-5.1L4 10l5.1-1.9zM18.5 15l.9 2.1 2.1.9-2.1.9-.9 2.1-.9-2.1-2.1-.9 2.1-.9z"/>',
  code: '<path d="m8 7-5 5 5 5M16 7l5 5-5 5M14 4l-4 16"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  external: '<path d="M14 4h6v6M20 4l-9 9M18 14v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4"/>',
  download: '<path d="M12 4v11M7 11l5 5 5-5M5 20h14"/>',
  bolt: '<path d="M13 3 5 14h6l-1 7 8-11h-6z"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2.5V5M12 19v2.5M2.5 12H5M19 12h2.5M5.3 5.3 7 7M17 17l1.7 1.7M5.3 18.7 7 17M17 7l1.7-1.7"/>',
  moon: '<path d="M20 14.2A8.3 8.3 0 0 1 9.8 4 8.3 8.3 0 1 0 20 14.2z"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  sync: '<path d="M4 9a8 8 0 0 1 14-3l2 2M20 4v4h-4M20 15a8 8 0 0 1-14 3l-2-2M4 20v-4h4"/>',
  trash: '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/>',
  back: '<path d="M19 12H5M11 6l-6 6 6 6"/>',
  plug: '<path d="M9 3v5M15 3v5M6 8h12v3a6 6 0 0 1-12 0zM12 17v4"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5.5M12 7.5v.2"/>',
  database: '<ellipse cx="12" cy="6" rx="8" ry="3"/><path d="M4 6v6c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>',
  lock: '<rect x="5" y="11" width="14" height="10" rx="2.5"/><path d="M8 11V7.5a4 4 0 0 1 8 0V11"/>',
  share: '<circle cx="6" cy="12" r="2.5"/><circle cx="18" cy="6" r="2.5"/><circle cx="18" cy="18" r="2.5"/><path d="m8.2 10.8 7.6-3.6M8.2 13.2l7.6 3.6"/>',
  browser: '<rect x="3" y="4" width="18" height="16" rx="2.5"/><path d="M3 9h18M6.5 6.5v.2M9.5 6.5v.2"/>',
  monitor: '<rect x="3" y="4" width="18" height="12.5" rx="2"/><path d="M8.5 20.5h7M12 16.5v4"/>',
  server: '<rect x="3" y="4" width="18" height="7" rx="2"/><rect x="3" y="13" width="18" height="7" rx="2"/><path d="M7 7.5v.2M7 16.5v.2M11 7.5h6M11 16.5h6"/>',
  book: '<path d="M5 19.5A2.5 2.5 0 0 1 7.5 17H19V3H7.5A2.5 2.5 0 0 0 5 5.5zM5 19.5A2.5 2.5 0 0 0 7.5 22H19v-5M9 7.5h6"/>',
  lanes: '<path d="M4 6h13M4 12h13M4 18h13M14.5 3.5 17 6l-2.5 2.5M14.5 9.5 17 12l-2.5 2.5M14.5 15.5 17 18l-2.5 2.5"/>',
  wrench: '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.4-3.4a6 6 0 0 1-7.9 7.9l-6.6 6.6a2.1 2.1 0 0 1-3-3l6.6-6.6a6 6 0 0 1 7.9-7.9z"/>',
  eye: '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  pencil: '<path d="M4 20h4L19.5 8.5l-4-4L4 16zM13 7l4 4"/>',
  pointer: '<path d="m4 4 6.5 16 2.3-6.9 6.9-2.3zM13.5 13.5 19 19"/>',
  chat: '<path d="M20.5 11.5a8 8 0 0 1-11.6 7.1L4 20l1.4-4.9A8 8 0 1 1 20.5 11.5z"/>',
  power: '<path d="M17.7 6.6a8 8 0 1 1-11.4 0M12 3v9"/>',
  shield: '<path d="M12 21s7.5-3.5 7.5-9.5V5.5L12 3 4.5 5.5v6C4.5 17.5 12 21 12 21z"/>',
  key: '<circle cx="7.5" cy="15.5" r="4.5"/><path d="M10.7 12.3 20 3M15.5 7.5l3 3M18.5 4.5 21 7"/>',
  eyeOff: '<path d="M4 4l16 16M9.9 5.2A9.6 9.6 0 0 1 12 5c6.4 0 10 7 10 7a17 17 0 0 1-3.1 4M6.4 6.5C3.6 8.4 2 12 2 12s3.6 7 10 7a9.7 9.7 0 0 0 4.2-.9M9.9 9.9a3 3 0 0 0 4.2 4.2"/>',
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

// Rounded first and split into units after, so a part never shows as "60".
export function formatDuration(seconds) {
  if (seconds < 9.95) return `${seconds.toFixed(1)}s`;
  const whole = Math.round(seconds);
  if (whole < 60) return `${whole}s`;
  if (whole < 3600) return `${Math.floor(whole / 60)}m ${whole % 60}s`;
  const minutes = Math.round(whole / 60);
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
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
  const note = h("div", { class: `toast ${tone}`, title: "Click to dismiss", onclick: () => note.remove() }, h("span", { text: message }));
  toasts.append(note);
  setTimeout(() => note.remove(), tone === "error" ? 9000 : 4000);
}
