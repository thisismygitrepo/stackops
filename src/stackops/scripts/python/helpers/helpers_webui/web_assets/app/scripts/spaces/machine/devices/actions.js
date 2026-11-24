import { toast } from "/assets/scripts/dom.js";
import { request } from "/assets/scripts/state.js";
import { confirmAction } from "../../../overlays.js";
import { isMounted } from "./model.js";
import { MOUNT_COMMAND, volumeName } from "./words.js";

const BUSY_NOTE = "If a program still has a file open on it, nothing happens and you are told which program.";
const listed = (names) => (names.length < 2 ? names.join("") : `${names.slice(0, -1).join(", ")} and ${names.at(-1)}`);

// What the page does to a volume or a disk. Mounting in the usual place and unmounting are done by the server straight away; ejecting and
// unmounting ask first, since something may be in the middle of using the disk. Mounting with choices is handed to the mount tool.
// `view.busy` holds what is being worked on, so its button shows that and cannot be pressed twice.
export function createDeviceActions({ tools, view, repaint, reload }) {
  async function run(action, id, done) {
    if (view.busy.has(id)) return;
    view.busy.add(id);
    repaint();
    try {
      await request("POST", `/api/machine/devices/${action}`, { id });
      toast(done, "info");
    } catch (error) {
      toast(error.message);
    }
    view.busy.delete(id);
    await reload();
  }

  return {
    mount: (volume) => run("mount", volume.id, `${volumeName(volume)} is mounted.`),
    handOver: (volume) => tools.open(MOUNT_COMMAND, { preset: { device_query: volume.mount_query } }),
    async unmount(volume) {
      const name = volumeName(volume);
      const body = `Its files can no longer be reached at ${volume.mount_point} until it is mounted again. The disk stays connected. ${BUSY_NOTE}`;
      if (await confirmAction({ title: `Unmount ${name}?`, body, confirm: "Unmount" })) await run("unmount", volume.id, `${name} is unmounted.`);
    },
    async eject(group) {
      const names = group.volumes.filter(isMounted).map(volumeName);
      const first = names.length ? `${listed(names)} ${names.length === 1 ? "is" : "are"} unmounted first. ` : "";
      const image = group.disk.place === "image";
      const body = image ? `${first}The image is then closed. Its file stays where it is. ${BUSY_NOTE}` : `${first}After that the disk can be unplugged. ${BUSY_NOTE}`;
      if (await confirmAction({ title: `Eject ${group.title}?`, body, confirm: "Eject" })) await run("eject", group.disk.id, image ? `${group.title} is closed.` : `${group.title} is ejected. It can be unplugged now.`);
    },
  };
}
