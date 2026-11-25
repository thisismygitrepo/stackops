// The purpose-built views of the Toolbox's Cloud storage collection, in the shape features.js describes. `load` paths are relative to this folder.
// OneDrive is one page that stands in for the whole collection: the Toolbox shows it in place of the collection's tool cards (CLOUD_COLLECTIONS),
// and each of its commands, opened from anywhere, leads to that page. `command` tells the page which of them it was.
const onedrive = () => import("../spaces/cloud/onedrive.js");
const ONEDRIVE_COMMANDS = ["auth", "status", "accounts", "list", "search", "download", "upload", "delete", "config-path", "add-account"];

export const CLOUD_FEATURES = ONEDRIVE_COMMANDS.map((command) => ({
  path: `cloud onedrive ${command}`,
  load: () => onedrive().then((page) => ({ open: (context, given) => page.open(context, { ...given, command }) })),
}));

// A collection's page, by the collection's path. Its module exports `createPart(context)`, which returns `{ element, show(rest) }`: `rest` is
// the part of the address past the collection's own.
export const CLOUD_COLLECTIONS = { "cloud onedrive": onedrive };
