from starlette.routing import Route

from stackops.scripts.python.helpers.helpers_webui.dotfiles_routes import dotfiles_routes
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_routes import machine_autostart_routes
from stackops.scripts.python.helpers.helpers_webui.machine_devices_routes import machine_devices_routes
from stackops.scripts.python.helpers.helpers_webui.machine_mount_routes import machine_mount_routes
from stackops.scripts.python.helpers.helpers_webui.machine_processes_routes import machine_processes_routes
from stackops.scripts.python.helpers.helpers_webui.machine_update_routes import machine_update_routes
from stackops.scripts.python.helpers.helpers_webui.machine_windows_routes import machine_windows_routes
from stackops.scripts.python.helpers.helpers_webui.network_routes import network_routes
from stackops.scripts.python.helpers.helpers_webui.security_routes import security_routes
from stackops.scripts.python.helpers.helpers_webui.settings_routes import settings_routes
from stackops.scripts.python.helpers.helpers_webui.terminal_ghostty_routes import terminal_ghostty_routes
from stackops.scripts.python.helpers.helpers_webui.terminal_multiplexer_routes import terminal_multiplexer_routes
from stackops.scripts.python.helpers.helpers_webui.terminal_shell_profile_routes import terminal_shell_profile_routes
from stackops.scripts.python.helpers.helpers_webui.terminal_starship_routes import terminal_starship_routes
from stackops.scripts.python.helpers.helpers_webui.terminal_wezterm_routes import terminal_wezterm_routes


# What the app view's purpose-built views read and change beyond what their commands print (`web_assets/app/scripts/features.js` lists the views).
# Each view keeps its routes in a module of its own, all of them under its own address: /api/terminal/<view>/ or /api/machine/<view>/.
def feature_routes() -> list[Route]:
    return [
        *terminal_multiplexer_routes(),
        *terminal_shell_profile_routes(),
        *terminal_starship_routes(),
        *terminal_wezterm_routes(),
        *terminal_ghostty_routes(),
        *machine_processes_routes(),
        *machine_autostart_routes(),
        *machine_devices_routes(),
        *machine_mount_routes(),
        *machine_windows_routes(),
        *machine_update_routes(),
        *settings_routes(),
        *dotfiles_routes(),
        *network_routes(),
        *security_routes(),
    ]
