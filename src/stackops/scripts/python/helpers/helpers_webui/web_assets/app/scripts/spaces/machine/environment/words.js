export const TOOL_PATH = "utils machine environment";
export const ENVIRONMENT_HASH = "#/machine/environment";
export const PATH_HASH = `${ENVIRONMENT_HASH}/path`;
export const ADDRESS = "/api/machine/environment";
export const TABS = [["variables", "Variables"], ["path", "Program search path"]];
// How many of a folder's programs are drawn at once. A folder can hold thousands, and a search narrows them.
export const PROGRAM_LIMIT = 300;
// A value that is a list of folders shows this many of them until its row is opened.
export const PARTS_SHOWN = 4;
// What a place on the search path is when it is not a folder that can be read.
export const UNUSABLE = { missing: "Missing", file: "Not a folder", unreadable: "Cannot be read" };
