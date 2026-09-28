import { C, box, text, lines, card, link, pill, frame } from './drawing.mjs';
import { transformation } from './transformation.mjs';

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

function scope(scene, focus) {
  let body = lines(scene.Title[0], 100, 225, 66, C.ink, 1720, 650)
    + text(scene.Subtitle[0], 104, 393, 31, C.muted, 400, false);
  const positions = [[100, 438, 553], [683, 438, 553], [1266, 438, 554], [100, 626, 845], [975, 626, 845]];
  scene.Card.forEach((value, i) => {
    const [x, y, width] = positions[i];
    const active = focus === 'software' ? i === 0 : focus === 'personal' ? i === 1 || i === 2 : i >= 3;
    body += card(value, x, y, width, 158, active);
  });
  return body;
}

function unified(scene, focus) {
  let body = lines(scene.Title[0], 100, 224, 64, C.ink, 1720, 650)
    + text(scene.Subtitle[0], 104, 387, 30, C.muted, 400, false);
  const all = focus === 'together';
  body += box(100, 429, 1720, 90, C.selected, C.accent, 18)
    + text('StackOps', 130, 487, 38, C.ink, 600, false)
    + text('Your digital life, managed as a whole', 595, 485, 33, C.accent, 500, false);
  for (let i = 0; i < 5; i++) {
    const x = 100 + i * 350;
    const active = all || (focus === 'setup' ? i < 3 : i >= 3);
    body += link(x + 160, 519, x + 160, 565, active)
      + card(scene.Card[i], x, 565, 320, 193, active);
  }
  return body;
}

function familiar(scene, focus) {
  let body = lines(scene.Title[0], 100, 230, 70, C.ink, 1720, 650)
    + text(scene.Subtitle[0], 104, 410, 33, C.muted, 400, false);
  body += box(100, 470, 1720, 112, C.selected, C.accent, 18)
    + text('The stack you are comfortable with', 390, 543, 49, C.ink, 600, false);
  if (focus === 'platforms') {
    scene.Card.forEach((value, i) => {
      const x = 100 + i * 590;
      body += link(x + 270, 582, x + 270, 627, true) + card(value, x, 627, 540, 150, true);
    });
  } else {
    body += pill('Your applications', 100, 653, 540, true)
      + pill('Your preferences', 690, 653, 540, true)
      + pill('Your way of working', 1280, 653, 540, true);
  }
  return body;
}

function closing(scene, focus) {
  let body = lines(scene.Title[0], 100, 292, 100, C.ink, 1720, 650)
    + text(scene.Subtitle[0], 104, 537, 42, C.muted, 400, false);
  body += box(100, 611, 1720, 142, C.selected, C.accent, 22)
    + text('99%', 134, 713, 91, C.accent, 650, false)
    + text('of your digital footprint', 382, 687, 37, C.ink, 500, false)
    + text('All wrapped into one solution.', 383, 731, 28, C.muted, 400, false);
  if (focus !== 'life') body += text(scene.Link[0], 1065, 697, 34, C.accent, 500, false);
  if (focus === 'platforms') body += pill('OS-agnostic · Linux · macOS · Windows', 104, 555, 690, true);
  return body;
}

const layouts = { footprint, transformation, scope, unified, familiar, closing };

export function artwork(scene, index, count, beat) {
  const draw = layouts[scene.Layout[0]];
  if (!draw) throw new Error(`Unknown layout: ${scene.Layout[0]}`);
  return frame(scene, index, count, draw(scene, scene.Focus[beat]), beat);
}
