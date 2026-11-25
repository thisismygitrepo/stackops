// What a file is, from the ending of its name. The order is fixed and so is each kind's colour (cloud_onedrive.css): a kind looks the same in
// every folder, whatever else is in it. "Other" comes last and wears the quiet grey.
export const KINDS = [
  { id: "document", label: "Documents", one: "Document", endings: "pdf doc docx odt rtf txt md pages xls xlsx csv ods numbers ppt pptx key odp" },
  { id: "picture", label: "Pictures", one: "Picture", endings: "jpg jpeg png gif webp heic heif svg bmp tif tiff raw" },
  { id: "video", label: "Videos", one: "Video", endings: "mp4 mov mkv avi webm m4v wmv" },
  { id: "audio", label: "Audio", one: "Audio", endings: "mp3 wav flac m4a aac ogg wma" },
  { id: "archive", label: "Archives", one: "Archive", endings: "zip tar gz tgz 7z rar bz2 xz dmg iso" },
  { id: "code", label: "Code", one: "Code", endings: "py js ts json yaml yml toml sh html css c cpp h rs go java ipynb sql xml" },
  { id: "other", label: "Other", one: "File", endings: "" },
];
const KIND_OF_ENDING = new Map(KINDS.flatMap((kind) => kind.endings.split(" ").filter(Boolean).map((ending) => [ending, kind.id])));

export const isFolder = (item) => item.type === "folder";
export const kindOf = (item) => (isFolder(item) ? "folder" : (KIND_OF_ENDING.get(item.name.includes(".") ? item.name.split(".").pop().toLowerCase() : "") ?? "other"));
export const kindWord = (kind) => (kind === "folder" ? "Folder" : KINDS.find((candidate) => candidate.id === kind).one);

export const joinPath = (folder, name) => (folder === "/" ? `/${name}` : `${folder}/${name}`);
export const parentOf = (path) => path.slice(0, path.lastIndexOf("/")) || "/";
export const nameOf = (path) => path.slice(path.lastIndexOf("/") + 1);

// The folder an item sits in, from what the drive says about its parent ("/drive/root:/Documents/My%20notes", percent-encoded). Null when the
// drive does not say, as it may for a search result: such an item can be opened on OneDrive's site but not addressed by a path here.
export function folderOf(item) {
  const text = item.parent_path ?? "";
  const marker = text.indexOf("root:");
  if (marker < 0) return null;
  const path = text.slice(marker + "root:".length);
  try {
    return decodeURIComponent(path) || "/";
  } catch {
    return path || "/";
  }
}

export const PAGE_ADDRESS = "#/tools/cloud/onedrive";
// A folder of an account has an address of its own under the page's, so Back steps through the folders that were opened. "files" marks it off
// from the names of the collection's commands, which the Toolbox also reads at that place.
export const FILES_WORD = "files";
export const addressOf = (account, folder = "/") => `${PAGE_ADDRESS}/${[FILES_WORD, account, ...folder.split("/").filter(Boolean)].map(encodeURIComponent).join("/")}`;

// Only an https address is offered as a link: these come from the drive's answers, and nothing else should be opened from them.
export const safeLink = (address) => (typeof address === "string" && address.startsWith("https://") ? address : null);
