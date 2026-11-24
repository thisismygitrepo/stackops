// Not built yet: the tool's own form.
export function open({ tools }, { preset }) {
  return tools.open("utils machine kill-process", { preset, plain: true });
}
