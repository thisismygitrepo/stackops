import { plural } from "../../words.js";

// Why the install command leaves an app of a scan alone, in the words of the page. Keyed by the reason the server gives.
export const INSTALL_REASONS = {
  unfinished: () => "The scan did not finish, so nothing in it is installed.",
  no_result: () => "The scan never got an answer about this file.",
  check_failed: () => "Its check failed, so nothing is known about it.",
  no_verdict: () => "No engine gave a verdict on it.",
  flagged: (row) => `${plural(row.flagged_engines, "engine")} of ${row.verdict_engines} flagged it.`,
  no_copy: () => "The scan kept no cloud copy of it.",
  no_fingerprint: () => "The scan recorded no fingerprint for it, so a download could not be checked.",
};

// What each file of an export is, beside its name.
export const EXPORT_FILES = {
  "run.json": "The whole saved record, as the scan wrote it",
  "apps.csv": "One row per checked file, with its verdict",
  "engines.csv": "One row per answer an engine gave",
  "accounts.csv": "VirusTotal requests, counted per account",
};

// The names of the cloud services rclone knows by a short word. One that is not listed is shown by that word.
const CLOUD_KINDS = {
  drive: "Google Drive", onedrive: "OneDrive", dropbox: "Dropbox", s3: "S3 storage", box: "Box", pcloud: "pCloud", mega: "MEGA", b2: "Backblaze B2",
  sftp: "a server over SFTP", webdav: "WebDAV", googlecloudstorage: "Google Cloud Storage", azureblob: "Azure Blob Storage", protondrive: "Proton Drive", local: "a folder on this machine",
};
export const cloudKind = (kind) => CLOUD_KINDS[kind] ?? kind;

// Why an upload cannot start, with the way forward. `tool` names a StackOps tool to open, `hash` a page to go to, `command` something to run in a terminal.
export const CLOUD_PROBLEMS = {
  no_rclone: { title: "rclone is not installed", body: "Uploads go through rclone, the program that talks to cloud storage. Install it, add your cloud account to it, then come back.", action: "Find rclone under Apps", hash: "#/apps" },
  no_remotes: { title: "No cloud account is set up yet", body: "rclone is installed but knows no cloud account. Add one in a terminal with the command below. It asks which service and signs you in.", command: "rclone config" },
  no_default: { title: "No cloud is chosen for uploads", body: "rclone knows your cloud accounts, but StackOps has not been told which one to use.", action: "Choose a cloud", tool: "devops config setup cloud" },
  default_gone: { title: "The chosen cloud is gone", body: "StackOps is set to use a cloud account that rclone no longer has. Choose one that it does.", action: "Choose a cloud", tool: "devops config setup cloud" },
  unreadable: { title: "rclone's accounts could not be read", body: "rclone is installed, but asking it for its cloud accounts failed." },
};

export const UPLOAD_PROBLEMS = {
  missing: "There is no file at this path.",
  not_file: "This is a folder. An upload takes one file.",
  outside_home: "Only a file inside your home folder can be uploaded. Its place in the cloud is worked out from where it sits under the home folder.",
};

// What Google Drive said about a pasted link, as a tone and a sentence. "found" is put into words by the view, with the file's name and size.
export const LINK_STATES = {
  private: ["bad", "This file is not shared with everyone who has the link, so it cannot be downloaded here. Ask its owner to change the sharing."],
  missing: ["bad", "Google Drive has no file with this ID. Check that the whole link was pasted."],
  busy: ["warn", "Google Drive says too many people fetched this file lately. A download may fail until that passes."],
  offline: ["warn", "Google Drive could not be reached, so the link was not checked. You can still try the download."],
  unknown: ["warn", "Google Drive answered, but not in a way that says what this file is. You can still try the download."],
};
export const LINK_FORMS = {
  folder: ["bad", "This is a link to a folder. A download takes one file, so open the folder and copy the link of the file you want."],
  unrecognised: ["bad", "This does not look like a Google Drive link or file ID."],
};

// Why GPG would not encrypt for a key that is on this machine, for the key's row.
export const KEY_STATES = {
  expired: "Expired", revoked: "Revoked", disabled: "Turned off in GPG", cannot_encrypt: "Made for signing, not for encrypting",
  untrusted: "GPG has not been told to trust it, so it will not use it unasked",
};

export const LOOK_PROBLEMS = {
  missing: "There is nothing at this path.",
  not_file: "This is a folder. Only one encrypted file can be decrypted.",
  not_gpg_name: "Only a file whose name ends in .gpg can be decrypted here.",
  no_name: "Nothing is left of this name once the endings are taken off, so the result would have no name. Rename the file first.",
  overlap: "The result would land on or inside what is being read. Choose another place for it.",
};

export const RUN_FAILURES = {
  wrong_password: "The password was not accepted. Nothing was written.",
  needs_key: "This file was encrypted for a key, not with a password. Choose \"With a key\" and try again.",
  exists: "Something is already at the place for the result. Turn on replacing it, or choose another place.",
  overlap: "The result would land on or inside what is being read. Choose another place for it.",
};
