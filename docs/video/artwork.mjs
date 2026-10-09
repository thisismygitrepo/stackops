import { C, box, text, lines, card, pill, frame } from './drawing.mjs';
import { transformation } from './transformation.mjs';
import { store } from './store.mjs';

function footprint(scene, focus) {
  if (focus === 'opening') {
    return lines(scene.Opening[0], 100, 345, 88, C.ink, 1720, 650);
  }
  let body = text(scene.Title[0], 100, 255, 102, C.ink, 650, false)
    + text('Digital Life Manager', 104, 330, 42, C.muted, 400, false)
    + text('99%', 92, 590, 226, C.accent, 650, false)
    + text('of your digital footprint.', 104, 665, 48, C.ink, 500, false);
  if (focus === 'together') body += box(1058, 172, 784, 594, 'none', C.accent, 24);
  body += scene.Card.map((value, i) => card(value, 1080 + i % 2 * 380, 194 + Math.floor(i / 2) * 190, 358, 168, focus === value.split(' | ')[0].toLowerCase())).join('');
  if (focus === 'together') body += pill('OS-agnostic · Linux · macOS · Windows', 104, 715, 690, true);
  return body;
}

function familiar(scene, focus) {
  let body = lines(scene.Title[0], 100, 230, 70, C.ink, 1720, 650)
    + text(scene.Subtitle[0], 104, 410, 33, C.muted, 400, false);
  if (focus === 'roles') {
    body += box(100, 470, 1720, 112, C.selected, C.accent, 18)
      + `<g text-anchor="middle">${text(scene.Role[4], 960, 543, 49, C.ink, 600, false)}</g>`;
    body += scene.Role.slice(0, 4).map((value, i) => pill(value, 100 + i * 440, 653, 400, true)).join('');
    return body;
  }
  body += box(100, 470, 1720, 112, C.selected, C.accent, 18)
    + text('The stack you are comfortable with', 390, 543, 49, C.ink, 600, false)
    + pill('Your applications', 100, 653, 540, true)
    + pill('Your preferences', 690, 653, 540, true)
    + pill('Your way of working', 1280, 653, 540, true);
  return body;
}

function closing(scene, focus) {
  let body = lines(scene.Title[0], 100, 292, 100, C.ink, 1720, 650);
  if (focus === 'recipe') {
    body += text(scene.Recipe[0], 104, 517, 48, C.ink, 600, false)
      + text(scene['Recipe-detail'][0], 104, 571, 36, C.muted, 400, false);
  } else {
    body += text(scene.Subtitle[0], 104, 537, 42, C.muted, 400, false);
  }
  body += box(100, 611, 1720, 142, C.selected, C.accent, 22)
    + text('99%', 134, 713, 91, C.accent, 650, false)
    + text('of your digital footprint', 382, 687, 37, C.ink, 500, false)
    + text('All wrapped into one solution.', 383, 731, 28, C.muted, 400, false);
  if (focus !== 'life') body += text(scene.Link[0], 1065, 697, 34, C.accent, 500, false);
  return body;
}

const layouts = { footprint, transformation, store, familiar, closing };

export function artwork(scene, index, count, beat) {
  const draw = layouts[scene.Layout[0]];
  if (!draw) throw new Error(`Unknown layout: ${scene.Layout[0]}`);
  return frame(scene, index, count, draw(scene, scene.Focus[beat]), beat);
}
