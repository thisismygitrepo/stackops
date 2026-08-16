from io import StringIO
from pathlib import Path

from rich.console import Console

from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_models import (
    DetachedBrowserLaunchResult,
    ExistingBrowserLaunchResult,
    TmuxBrowserLaunchResult,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_rich_output import build_browser_launch_summary, build_browser_launches_summary
from stackops.scripts.python.helpers.helpers_agents.agents_browser_tmux_models import BrowserTmuxLaunch
from stackops.utils.network.address import InterfaceIPv4Address


def test_detached_lan_summary_shows_selected_endpoint_relay_and_warning() -> None:
    result = DetachedBrowserLaunchResult(
        browser="chrome",
        browser_path=Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        command=("chrome.exe", "--remote-debugging-port=57632"),
        endpoint_label="Chrome DevTools Protocol",
        endpoint_short_label="CDP",
        process_label="Chrome",
        host="0.0.0.0",
        port=9000,
        browser_port=57632,
        profile_path=Path(r"C:\Users\eng_a\data\browsers-profiles\chrome\p1"),
        prompt_path=Path(r"C:\Users\eng_a\code\agents\browser\vercel\prompts\chrome-p1.md"),
        process_id=30852,
        relay_process_id=17176,
    )
    lan_address = InterfaceIPv4Address(interface="Ethernet", ipv4_address="10.0.26.200", mac_address="00:11:22:33:44:55")
    output = StringIO()
    console = Console(file=output, width=120, color_system=None)

    console.print(build_browser_launch_summary(result=result, lan_address=lan_address))

    rendered_output = output.getvalue()
    assert "✓ Chrome launched" in rendered_output
    assert "PID 30852 · detached" in rendered_output
    assert "PID 17176 → 127.0.0.1:57632" in rendered_output
    assert "CDP bind" in rendered_output
    assert "0.0.0.0:9000" in rendered_output
    assert "CDP LAN" in rendered_output
    assert "http://10.0.26.200:9000 · Ethernet" in rendered_output
    assert "⚠ LAN exposure" in rendered_output
    assert "Use this only on a trusted network." in rendered_output


def test_non_lan_tmux_summary_shows_session_windows_and_attach_command() -> None:
    result = TmuxBrowserLaunchResult(
        browser="chrome",
        browser_path=Path("/usr/bin/google-chrome"),
        command=("/usr/bin/google-chrome", "--remote-debugging-port=9331"),
        endpoint_label="Chrome DevTools Protocol",
        endpoint_short_label="CDP",
        process_label="Chrome",
        host="127.0.0.1",
        port=9331,
        browser_port=9331,
        profile_path=Path("/tmp/stackops-browser-profiles/chrome-9331"),
        prompt_path=Path("/tmp/browser-prompt.md"),
        tmux=BrowserTmuxLaunch(
            session_name="stackops-browser",
            browser_window_name="chrome-9331",
            relay_window_name=None,
            attach_command=("tmux", "attach-session", "-t", "stackops-browser"),
        ),
    )
    output = StringIO()
    console = Console(file=output, width=120, color_system=None)

    console.print(build_browser_launch_summary(result=result, lan_address=None))

    rendered_output = output.getvalue()
    assert "✓ Chrome launched" in rendered_output
    assert "tmux · session stackops-browser" in rendered_output
    assert "Browser window" in rendered_output
    assert "chrome-9331" in rendered_output
    assert "tmux attach-session -t stackops-browser" in rendered_output
    assert "CDP" in rendered_output
    assert "127.0.0.1:9331" in rendered_output
    assert "CDP bind" not in rendered_output
    assert "Relay window" not in rendered_output
    assert "LAN exposure" not in rendered_output


def test_non_lan_existing_summary_shows_owner_and_opened_page_action() -> None:
    result = ExistingBrowserLaunchResult(
        browser="edge",
        browser_path=Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        command=("msedge.exe", "--remote-debugging-port=9331"),
        endpoint_label="Chrome DevTools Protocol",
        endpoint_short_label="CDP",
        process_label="Edge",
        host="127.0.0.1",
        port=9331,
        browser_port=9331,
        profile_path=None,
        prompt_path=Path(r"C:\Users\eng_a\code\agents\browser\vercel\prompts\edge-temp.md"),
        process_id=42100,
        owner="external",
        opened_page=True,
        repaired_relay=False,
    )
    output = StringIO()
    console = Console(file=output, width=120, color_system=None)

    console.print(build_browser_launch_summary(result=result, lan_address=None))

    rendered_output = output.getvalue()
    assert "✓ Edge ready" in rendered_output
    assert "PID 42100 · existing external" in rendered_output
    assert "Opened a page because the endpoint had no page targets" in rendered_output
    assert "Restarted the missing LAN relay" not in rendered_output
    assert "Profile" not in rendered_output
    assert "LAN exposure" not in rendered_output


def test_batch_lan_summary_shows_one_row_per_profile_and_shared_interface_warning() -> None:
    lan_address = InterfaceIPv4Address(interface="Ethernet", ipv4_address="10.0.26.200", mac_address=None)
    results = tuple(
        DetachedBrowserLaunchResult(
            browser="chrome",
            browser_path=Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            command=("chrome.exe",),
            endpoint_label="Chrome DevTools Protocol",
            endpoint_short_label="CDP",
            process_label="Chrome",
            host="0.0.0.0",
            port=port,
            browser_port=57000 + index,
            profile_path=Path(rf"C:\Users\eng_a\data\browsers-profiles\chrome\p{index}"),
            prompt_path=Path(rf"C:\Users\eng_a\code\agents\browser\vercel\prompts\chrome-p{index}.md"),
            process_id=30000 + index,
            relay_process_id=31000 + index,
        )
        for index, port in enumerate((60001, 60002), start=1)
    )
    output = StringIO()
    console = Console(file=output, width=180, color_system=None)

    console.print(build_browser_launches_summary(results=results, lan_address=lan_address))

    rendered_output = output.getvalue()
    assert "Chrome profiles ready · 2 endpoint(s)" in rendered_output
    assert "p1" in rendered_output
    assert "p2" in rendered_output
    assert "10.0.26.200" in rendered_output
    assert "60001" in rendered_output
    assert "60002" in rendered_output
    assert "Ethernet" in rendered_output
    assert rendered_output.count("LAN exposure") == 1
