import shlex

from stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_execution import (
    build_tmux_attach_or_switch_command,
)


def build_tmux_launch_command(mount_commands: dict[str, str], mount_locations: dict[str, str], session_name: str) -> str:
    commands: list[str] = ["set -e"]
    session_target = f"={session_name}:"

    for cloud_name, mount_cmd in mount_commands.items():
        window_target = f"={session_name}:={cloud_name}"
        mount_loc = mount_locations[cloud_name]

        mount_pane_cmd = f"bash -lc {shlex.quote(mount_cmd)}"
        about_pane_cmd = f"bash -lc {shlex.quote(f'rclone about {cloud_name}:; exec bash')}"
        explorer_pane_cmd = f"bash -lc {shlex.quote(f'yazi {shlex.quote(mount_loc)}')}"
        monitor_pane_cmd = f"bash -lc {shlex.quote('btm --default_widget_type net --expanded')}"
        shell_pane_cmd = f"bash -lc {shlex.quote(f'cd {shlex.quote(mount_loc)}; exec bash')}"

        commands.append(f"""if ! tmux list-panes -t {shlex.quote(window_target)} >/dev/null 2>&1; then""")
        commands.append(f"""if tmux has-session -t {shlex.quote(f'={session_name}')} 2>/dev/null; then""")
        commands.append(f"""tmux new-window -d -t {shlex.quote(session_target)} -n {shlex.quote(cloud_name)} {shlex.quote(mount_pane_cmd)}""")
        commands.append("else")
        commands.append(f"""tmux new-session -d -s {shlex.quote(session_name)} -n {shlex.quote(cloud_name)}""")
        commands.append(f"""tmux send-keys -t {shlex.quote(window_target)} {shlex.quote(mount_pane_cmd)} Enter""")
        commands.append("fi")
        commands.append(f"""tmux set-window-option -t {shlex.quote(window_target)} allow-rename off""")

        commands.append(f"tmux split-window -h -t {shlex.quote(window_target)} {shlex.quote(about_pane_cmd)}")
        commands.append(f"tmux select-pane -t {shlex.quote(window_target)}.0")
        commands.append(f"tmux split-window -v -t {shlex.quote(window_target)}.0 {shlex.quote(explorer_pane_cmd)}")
        commands.append(f"tmux select-pane -t {shlex.quote(window_target)}.1")
        commands.append(f"tmux split-window -v -t {shlex.quote(window_target)}.1 {shlex.quote(monitor_pane_cmd)}")
        commands.append(f"tmux select-pane -t {shlex.quote(window_target)}.2")
        commands.append(f"tmux split-window -v -t {shlex.quote(window_target)}.2 {shlex.quote(shell_pane_cmd)}")
        commands.append(f"tmux select-pane -t {shlex.quote(window_target)}.4")
        commands.append(f"tmux select-layout -t {shlex.quote(window_target)} tiled")
        commands.append("fi")

    first_cloud = next(iter(mount_commands))
    commands.append(f"""tmux select-window -t {shlex.quote(f'={session_name}:={first_cloud}')}""")
    commands.append(build_tmux_attach_or_switch_command(session_name=f"""={session_name}"""))
    return "\n".join(commands)
