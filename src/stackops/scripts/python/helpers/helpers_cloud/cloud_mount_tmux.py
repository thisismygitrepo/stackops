import shlex

from stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_execution import (
    build_tmux_attach_or_switch_command,
)


def build_mount_pane_command(mount_command: str) -> str:
    script = f"""trap 'trap "" HUP INT TERM; if [ -n "$!" ]; then kill -TERM "$!"; wait "$!"; fi; exit' HUP INT TERM
{mount_command} <&0 &
wait "$!"
"""
    return f"""bash -lc {shlex.quote(script)}"""


def build_tmux_launch_command(
    mount_commands: dict[str, str], mount_locations: dict[str, str], session_name: str, unmounted_clouds: set[str]
) -> str:
    commands: list[str] = ["set -e"]
    session_target = f"={session_name}:"

    for cloud_name, mount_cmd in mount_commands.items():
        window_target = f"={session_name}:={cloud_name}"
        mount_loc = mount_locations[cloud_name]

        mount_pane_cmd = build_mount_pane_command(mount_command=mount_cmd)
        about_pane_cmd = f"bash -lc {shlex.quote(f'rclone about {cloud_name}:; exec bash')}"
        explorer_pane_cmd = f"bash -lc {shlex.quote(f'yazi {shlex.quote(mount_loc)}')}"
        monitor_pane_cmd = f"bash -lc {shlex.quote('btm --default_widget_type net --expanded')}"
        shell_pane_cmd = f"bash -lc {shlex.quote(f'cd {shlex.quote(mount_loc)}; exec bash')}"

        commands.append(f"""if ! tmux list-panes -t {shlex.quote(window_target)} >/dev/null 2>&1; then""")
        commands.append(f"""if tmux has-session -t {shlex.quote(f'={session_name}')} 2>/dev/null; then""")
        commands.append(f"""mount_pane=$(tmux new-window -d -P -F '#{{pane_id}}' -t {shlex.quote(session_target)} -n {shlex.quote(cloud_name)} {shlex.quote(mount_pane_cmd)})""")
        commands.append("else")
        commands.append(f"""mount_pane=$(tmux new-session -d -P -F '#{{pane_id}}' -s {shlex.quote(session_name)} -n {shlex.quote(cloud_name)} {shlex.quote(mount_pane_cmd)})""")
        commands.append("fi")
        commands.append("""window_id=$(tmux display-message -p -t "$mount_pane" '#{window_id}')""")
        commands.append("""tmux set-window-option -t "$window_id" allow-rename off""")
        commands.append('tmux set-window-option -t "$window_id" @cloud-mount-service "$mount_pane"')

        commands.append(f"""about_pane=$(tmux split-window -d -h -P -F '#{{pane_id}}' -t "$mount_pane" {shlex.quote(about_pane_cmd)})""")
        commands.append(f"""explorer_pane=$(tmux split-window -d -v -P -F '#{{pane_id}}' -t "$mount_pane" {shlex.quote(explorer_pane_cmd)})""")
        commands.append(f"""tmux split-window -d -v -t "$about_pane" {shlex.quote(monitor_pane_cmd)}""")
        commands.append(f"""shell_pane=$(tmux split-window -d -v -P -F '#{{pane_id}}' -t "$explorer_pane" {shlex.quote(shell_pane_cmd)})""")
        commands.append('tmux select-pane -t "$shell_pane"')
        commands.append("""tmux select-layout -t "$window_id" tiled""")
        if cloud_name in unmounted_clouds:
            commands.append("else")
            commands.append(f"""window_id=$(tmux display-message -p -t {shlex.quote(window_target)} '#{{window_id}}')""")
            commands.append('mount_lock="cloud-mount-service-$window_id"')
            commands.append('tmux wait-for -L "$mount_lock"')
            commands.append("""trap 'tmux wait-for -U "$mount_lock"' EXIT""")
            commands.append('mount_pane=$(tmux show-options -wqv -t "$window_id" @cloud-mount-service)')
            commands.append("""if [ -z "$mount_pane" ] || [ "$(tmux display-message -p -t "$mount_pane" '#{pane_dead}' 2>/dev/null)" != 0 ]; then""")
            commands.append(f"""mount_pane=$(tmux split-window -d -h -P -F '#{{pane_id}}' -t "$window_id" {shlex.quote(mount_pane_cmd)})""")
            commands.append('tmux set-window-option -t "$window_id" @cloud-mount-service "$mount_pane"')
            commands.append("""tmux select-layout -t "$window_id" tiled""")
            commands.append("fi")
            commands.append('tmux wait-for -U "$mount_lock"')
            commands.append("trap - EXIT")
        commands.append("fi")

    first_cloud = next(iter(mount_commands))
    commands.append(f"""tmux select-window -t {shlex.quote(f'={session_name}:={first_cloud}')}""")
    commands.append(build_tmux_attach_or_switch_command(session_name=f"""={session_name}"""))
    return "\n".join(commands)
