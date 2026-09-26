from typing import Final


OPENROUTER_ZDR_EXTENSION_PATH: Final[str] = ".pi/extensions/stackops-openrouter-zdr.ts"
OPENROUTER_ZDR_EXTENSION_SETTING: Final[str] = "extensions/stackops-openrouter-zdr.ts"
OPENROUTER_ZDR_EXTENSION: Final[str] = """import type { Api, Model, StreamOptions } from "@earendil-works/pi-ai";
import { openrouterProvider } from "@earendil-works/pi-ai/providers/openrouter";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

function withZdr<T extends StreamOptions>(options: T): T {
  return {
    ...options,
    onPayload: async (payload: unknown, model: Model<Api>): Promise<unknown> => {
      const replacement = await options.onPayload?.(payload, model);
      const request = (replacement === undefined ? payload : replacement) as { provider?: Record<string, unknown> };
      return { ...request, provider: { ...request.provider, zdr: true } };
    },
  };
}

export default function openRouterZdr(pi: ExtensionAPI): void {
  const provider = openrouterProvider();
  const protectedProvider: typeof provider = {
    ...provider,
    stream: (model, context, options) => provider.stream(model, context, withZdr(options ?? {})),
    streamSimple: (model, context, options) => provider.streamSimple(model, context, withZdr(options ?? {})),
  };
  pi.registerProvider(protectedProvider);
}
"""
