export const C = { bg: '#101019', panel: '#1c1b2c', edge: '#3c3854', ink: '#f8f6ff', muted: '#b6b0cc', accent: '#a78bfa', violet: '#8b5cf6', selected: '#30224e', soft: '#242033', mint: '#8ee0c2' };

export const esc = value => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
export const box = (x, y, w, h, fill, stroke, radius) => `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${radius}" fill="${fill}" stroke="${stroke}" stroke-width="2"/>`;
export const text = (value, x, y, size, color, weight, mono) => `<text x="${x}" y="${y}" font-family="${mono ? 'Menlo, monospace' : 'Helvetica Neue, Helvetica, sans-serif'}" font-size="${size}" font-weight="${weight}" fill="${color}">${esc(value)}</text>`;

export function lines(value, x, y, size, color, width, weight) {
  const result = [];
  for (const part of value.split('|')) {
    let current = '';
    for (const word of part.trim().split(/\s+/)) {
      if ((current.length + word.length + 1) * size * 0.54 > width && current) { result.push(current); current = ''; }
      current += (current ? ' ' : '') + word;
    }
    result.push(current);
  }
  return result.map((line, index) => text(line, x, y + index * size * 1.22, size, color, weight, false)).join('');
}

export function card(value, x, y, w, h, active) {
  const [title, detail] = value.split(' | ');
  return box(x, y, w, h, active ? C.selected : C.panel, active ? C.accent : C.edge, 18)
    + box(x + 24, y + 24, 28, 4, active ? C.accent : C.edge, 'none', 2)
    + lines(title, x + 24, y + 70, 28, C.ink, w - 48, 600)
    + lines(detail, x + 24, y + 112, 24, C.muted, w - 48, 400);
}

export function link(x1, y1, x2, y2, active) {
  const midpoint = (x1 + x2) / 2;
  return `<path d="M${x1} ${y1} C${midpoint} ${y1} ${midpoint} ${y2} ${x2} ${y2}" fill="none" stroke="${active ? C.accent : C.edge}" stroke-width="${active ? 3 : 2}"/>`
    + `<circle cx="${x2}" cy="${y2}" r="4" fill="${active ? C.accent : C.edge}"/>`;
}

export function pill(value, x, y, w, active) {
  return box(x, y, w, 48, active ? C.selected : C.panel, active ? C.accent : C.edge, 24)
    + text(value, x + 20, y + 32, 22, active ? C.ink : C.muted, 500, false);
}

export function frame(scene, index, count, body, beat) {
  const progress = scene.Say.map((_, i) => box(100 + i * 40, 795, 26, 4, i <= beat ? C.accent : C.edge, 'none', 2)).join('');
  return `<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080">
    <defs><radialGradient id="glow"><stop stop-color="#462875"/><stop offset="1" stop-color="${C.bg}"/></radialGradient></defs>
    <rect width="1920" height="1080" fill="${C.bg}"/><ellipse cx="1670" cy="140" rx="1000" ry="800" fill="url(#glow)" opacity=".34"/>
    <path d="M100 52h25v10h-25zm8 15h25v10h-25zm8 15h25v10h-25z" fill="${C.accent}"/>
    ${text('STACKOPS', 159, 80, 27, C.ink, 600, false)}
    ${text(scene.Eyebrow[0], 425, 78, 20, C.accent, 500, true)}
    ${text(String(index + 1).padStart(2, '0') + ' / ' + String(count).padStart(2, '0'), 1680, 78, 22, C.muted, 400, true)}
    <path d="M100 116H1820" stroke="${C.edge}"/>${body}${progress}
    ${text(scene.Takeaway[0], 100, 850, 28, C.accent, 500, false)}
    <path d="M100 884H1820" stroke="${C.edge}"/>
    ${text('CONCEPTUAL ILLUSTRATION', 100, 1040, 15, C.muted, 400, true)}
    ${text('StackOps · Digital Life Manager', 1480, 1040, 19, C.muted, 400, false)}
  </svg>`;
}
