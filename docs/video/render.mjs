import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';

const folder = dirname(fileURLToPath(import.meta.url));
const root = resolve(folder, '../..');
const scratch = resolve(root, '.ai/tmp_scripts/stackops-video');
mkdirSync(scratch, { recursive: true });
const scenes = [];
let scene;
for (const line of readFileSync(resolve(folder, 'stackops-concept.rst'), 'utf8').split('\n')) {
  if (/^Scene \d+/.test(line)) { scene = {}; scenes.push(scene); }
  const field = line.match(/^:([\w-]+): (.*)$/);
  if (field && scene) (scene[field[1]] ??= []).push(field[2]);
}
const C = { bg: '#0b1420', panel: '#142536', edge: '#294257', ink: '#f4f7fa', muted: '#a8bdce', green: '#76e4b3', blue: '#86bbff', gold: '#f7cc86' };
const esc = value => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
const box = (x, y, w, h, fill, stroke, radius) => `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${radius}" fill="${fill}" stroke="${stroke}"/>`;
const text = (value, x, y, size, color, weight, mono) => `<text x="${x}" y="${y}" font-family="${mono ? 'Menlo, monospace' : 'Helvetica Neue, Helvetica, sans-serif'}" font-size="${size}" font-weight="${weight}" fill="${color}">${esc(value)}</text>`;
function lines(value, x, y, size, color, width, weight) {
  const result = []; let current = '';
  for (const part of value.split('|')) {
    for (const word of part.trim().split(/\s+/)) {
      if ((current.length + word.length + 1) * size * 0.53 > width && current) { result.push(current); current = ''; }
      current += (current ? ' ' : '') + word;
    }
    result.push(current); current = '';
  }
  return result.map((line, i) => text(line, x, y + i * size * 1.22, size, color, weight, false)).join('');
}
function card(value, x, y, w, h, index) {
  const [title, detail] = value.split(' | ');
  return box(x, y, w, h, C.panel, C.edge, 20) + text(String(index + 1).padStart(2, '0'), x + 26, y + 42, 20, C.green, 500, true)
    + lines(title, x + 26, y + 92, 31, C.ink, w - 52, 600) + lines(detail, x + 26, y + 141, 25, C.muted, w - 52, 400);
}
function command(values, y, width, size) {
  return box(100, y, width, 58 + values.length * 50, '#07101a', C.edge, 18)
    + text('COMMAND EXAMPLE', 128, y + 32, 16, C.muted, 500, true)
    + values.map((value, i) => text('$', 130, y + 78 + i * 50, size, C.green, 500, true) + text(value, 164, y + 78 + i * 50, size, C.ink, 400, true)).join('');
}
function arrows(y) {
  return [654, 1244].map(x => `<path d="M ${x} ${y} h 52 m -14 -12 l 14 12 -14 12" fill="none" stroke="${C.green}" stroke-width="3"/>`).join('');
}
function artwork(s, index) {
  const title = s.Title[0], subtitle = s.Subtitle[0], cards = s.Card ?? [];
  let body = '';
  switch (s.Layout[0]) {
    case 'intro':
      body = lines(title, 100, 328, 88, C.ink, 1000, 650) + lines(subtitle, 104, 450, 31, C.muted, 860, 400)
        + text('stackops --help', 104, 690, 36, C.green, 500, true);
      body += cards.map((v, i) => card(v, 1120 + (i % 2) * 352, 225 + Math.floor(i / 2) * 208, 328, 184, i)).join('');
      break;
    case 'packages':
      body = lines(title, 100, 250, 80, C.ink, 950, 650) + lines(subtitle, 104, 490, 32, C.muted, 770, 400);
      body += cards.map((v, i) => {
        const [label, detail] = v.split(' | '); const y = 200 + i * 155;
        return box(1080, y, 738, 133, i === 0 ? '#193a38' : C.panel, i === 0 ? C.green : C.edge, 18)
          + text(i === 0 ? '→' : '·', 1110, y + 61, 38, C.green, 500, false)
          + text(label, 1170, y + 51, 33, C.ink, 600, false) + text(detail, 1170, y + 96, 26, C.muted, 400, false);
      }).join('');
      body += command(s.Command, 715, 1718, 33);
      break;
    case 'terminal':
      body = lines(title, 100, 260, 76, C.ink, 745, 650) + lines(subtitle, 104, 495, 31, C.muted, 620, 400);
      body += box(840, 194, 978, 465, '#08111c', C.edge, 18) + box(840, 194, 978, 58, '#1b3042', 'none', 18)
        + text('development / layout.json', 876, 231, 24, C.muted, 500, true);
      cards.forEach((value, i) => {
        const [label, cmd] = value.split(' | '); const x = i === 0 ? 860 : 1340; const y = i === 2 ? 463 : 270; const h = i === 0 ? 370 : 177;
        body += box(x, y, i === 0 ? 460 : 458, h, C.panel, C.edge, 10) + text(label, x + 22, y + 38, 23, C.green, 500, true)
          + text('$ ' + cmd, x + 22, y + 90, i === 1 ? 19 : 24, C.ink, 400, true);
        if (i === 0) body += [145, 182, 219, 256].map((dy, j) => box(x + 24, y + dy, 270 - j * 39, 8, j === 0 ? '#589e91' : '#304c63', 'none', 4)).join('');
      });
      body += command(s.Command, 715, 1718, 32);
      break;
    case 'helpers':
      body = lines(title, 100, 238, 75, C.ink, 1720, 650) + text(subtitle, 104, 326, 33, C.muted, 400, false)
        + cards.map((v, i) => card(v, 100 + i * 437, 430, 407, 267, i)).join('');
      break;
    case 'closing':
      body = lines(title, 100, 241, 80, C.ink, 1650, 650) + text(subtitle, 104, 436, 32, C.muted, 400, false)
        + command(s.Command, 506, 1718, 36) + text(s.Footnote[0], 104, 780, 39, C.green, 500, false);
      break;
    default: {
      body = lines(title, 100, 218, 70, C.ink, 1720, 650);
      const twoLines = title.includes('|');
      body += text(subtitle, 104, twoLines ? 372 : 310, 30, C.muted, 400, false);
      body += cards.map((v, i) => card(v, 100 + i * 590, 438, 540, 218, i)).join('');
      if (['config'].includes(s.Layout[0])) body += arrows(548);
      body += command(s.Command, 715, 1718, s.Layout[0] === 'movement' ? 30 : 33);
    }
  }
  if (s.Footnote && s.Layout[0] !== 'closing') body += text(s.Footnote[0], 104, 858, 22, C.muted, 400, false);
  return `<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080">
  <defs><radialGradient id="glow"><stop stop-color="#234457"/><stop offset="1" stop-color="${C.bg}"/></radialGradient></defs>
  <rect width="1920" height="1080" fill="${C.bg}"/><ellipse cx="1570" cy="160" rx="1250" ry="900" fill="url(#glow)" opacity=".55"/>
  <path d="M100 52h25v10h-25zm8 15h25v10h-25zm8 15h25v10h-25z" fill="${C.green}"/>
  ${text('STACKOPS', 159, 80, 27, C.ink, 600, false)}${text(s.Eyebrow[0], 430, 78, 22, C.green, 500, true)}
  ${text(String(index + 1).padStart(2, '0') + ' / ' + String(scenes.length).padStart(2, '0'), 1682, 78, 22, C.muted, 400, true)}
  <path d="M100 116H1818" stroke="${C.edge}"/>${body}
  <path d="M100 888H1818" stroke="${C.edge}"/>
  ${text('CONCEPTUAL ILLUSTRATION', 104, 1040, 15, '#738d9e', 400, true)}
  ${text('StackOps command examples', 1325, 1040, 19, '#738d9e', 400, false)}</svg>`;
}
const manifest = { output: resolve(folder, 'stackops-concept.mp4'), scratch, scenes: [] };
for (const [index, s] of scenes.entries()) {
  const prefix = resolve(scratch, `scene-${String(index + 1).padStart(2, '0')}`);
  writeFileSync(prefix + '.svg', artwork(s, index));
  execFileSync('rsvg-convert', ['-o', prefix + '.png', prefix + '.svg']);
  const captions = s.Say.map((value, clip) => {
    const audio = `${prefix}-${clip + 1}.aiff`;
    execFileSync('/usr/bin/say', ['-v', 'Samantha', '-r', '164', '-o', audio, value]);
    return { text: value, audio };
  });
  manifest.scenes.push({ image: prefix + '.png', captions });
  console.log(`Prepared scene ${index + 1}: ${s.Title[0].replaceAll('|', ' ')}`);
}
writeFileSync(resolve(scratch, 'manifest.json'), JSON.stringify(manifest, null, 2));
if (!process.argv.includes('--prepare-only')) {
  execFileSync('swiftc', ['-parse-as-library', '-O', '-module-cache-path', resolve(scratch, 'module-cache'), resolve(folder, 'encode.swift'), '-o', resolve(scratch, 'encode')], { stdio: 'inherit' });
  execFileSync(resolve(scratch, 'encode'), [resolve(scratch, 'manifest.json')], { stdio: 'inherit' });
}
