#!/usr/bin/env python3
"""
Example usage of the modularized Zellij remote layout generator.
"""

from rich.console import Console
from stackops.cluster.sessions_managers.zellij.zellij_remote import ZellijRemoteLayoutGenerator
from stackops.utils.schemas.layouts.layout_types import LayoutConfig

console = Console()


def example_usage():
    """Demonstrate the refactored modular usage."""

    # Sample layout configuration using new schema
    sample_layout: LayoutConfig = {
        "layoutName": "ExampleRemoteSession",
        "layoutTabs": [
            {"tabName": "🤖Bot1", "startDir": "~/code/bytesense/bithence", "command": "fire -mO go1.py bot1 -- --create_new_bot=True"},
            {"tabName": "🤖Bot2", "startDir": "~/code/bytesense/bithence", "command": "fire -mO go2.py bot2 -- --create_new_bot=True"},
            {"tabName": "📊Monitor", "startDir": "~", "command": "htop"},
            {"tabName": "📝Logs", "startDir": "/var/log", "command": "tail -f /var/log/app.log"},
        ],
    }

    # Replace 'myserver' with an actual SSH config alias
    remote_name = "myserver"  # This should be in ~/.ssh/config
    session_name = "test_remote_session"

    try:
        # Create layout using the remote generator
        generator = ZellijRemoteLayoutGenerator(remote_name=remote_name, session_name=session_name, layout_config=sample_layout)
        generator.create_layout_file()
        # Preview the layout content
        preview = generator.layout_generator.generate_layout_content(sample_layout)
        print(f"📄 Layout preview:\n{preview}")

        # Check status using the modular components
        print(f"\n🔍 Checking command status on remote '{remote_name}':")
        if not generator.layout_config:
            console.print("[bold red]❌ No layout config available[/bold red]")
        else:
            generator.status_reporter.print_status_report(generator.layout_config)

        # The individual components can also be used directly:
        print("\n🔧 Direct component usage examples:")

        # Use remote executor directly
        print(f"Remote executor: {generator.remote_executor.remote_name}")

        # Use layout generator directly
        layout_content = generator.layout_generator.generate_layout_content(sample_layout)
        print(f"Layout content length: {len(layout_content)} characters")

        # Use process monitor directly
        status = generator.process_monitor.check_all_commands_status(sample_layout)
        print(f"Command status check completed for {len(status)} commands")

        print("\n✅ All modular components working correctly!")

        # Uncomment these to actually start and attach to the session:
        # start_result = generator.start_zellij_session()
        # print(f"Session start result: {start_result}")
        # generator.attach_to_session()

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    example_usage()
