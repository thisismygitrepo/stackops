// Not built yet: the tool's own form.
export function open({ tools }, { preset }) {
  return tools.open("utils machine list-devices", { preset, plain: true });
}
