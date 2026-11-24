// The purpose-built views of the Security page, in the shape features.js describes. `load` paths are relative to this folder.
// Each is a sheet. Encrypt and decrypt open the same one, each on its own half.
export const SECURITY_FEATURES = [
  { path: "devops security install", load: () => import("../spaces/security/install.js") },
  { path: "devops security export", load: () => import("../spaces/security/export.js") },
  { path: "devops security upload", load: () => import("../spaces/security/upload.js") },
  { path: "devops security download", load: () => import("../spaces/security/download.js") },
  { path: "devops data encrypt", load: () => import("../spaces/security/encrypt.js") },
  { path: "devops data decrypt", load: () => import("../spaces/security/decrypt.js") },
];
