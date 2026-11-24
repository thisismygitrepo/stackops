// Not built yet: the tool's own form.
export function open({ tools }, { preset }) {
  return tools.open("devops config terminal config-shell", { preset, plain: true });
}
