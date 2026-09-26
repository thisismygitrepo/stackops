from typing import Final


OPENROUTER_ZDR_EXTENSION_PATH: Final[str] = ".omp/extensions/stackops-openrouter-zdr.ts"
OPENROUTER_ZDR_EXTENSION: Final[str] = """import type { ExtensionAPI } from "@oh-my-pi/pi-coding-agent";

export default function openRouterZdr(pi: ExtensionAPI): void {
  pi.on("before_provider_request", (event, ctx) => {
    const model = ctx.model;
    if (!model) return;
    const hostname = new URL(model.baseUrl).hostname;
    if (model.provider !== "openrouter" && hostname !== "openrouter.ai" && !hostname.endsWith(".openrouter.ai")) {
      return;
    }
    const payload = event.payload as { provider?: Record<string, unknown> };
    return { ...payload, provider: { ...payload.provider, zdr: true } };
  });
}
"""
