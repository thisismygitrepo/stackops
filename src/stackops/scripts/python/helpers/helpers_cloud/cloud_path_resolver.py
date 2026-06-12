from stackops.scripts.python.helpers.helpers_cloud.cloud_helpers import my_abs
from stackops.utils.cloud.defaults import CloudConfig
from stackops.utils.cloud.rclone_wrapper import get_remote_path
from stackops.utils.source_of_truth import read_stackops_config_string
from stackops.utils.accessories import pprint
from rich.console import Console
from rich.panel import Panel


ES = "^"  # chosen carefully to not mean anything on any shell. `$` was a bad choice.
console = Console()


def parse_cloud_source_target(
    cloud_config_explicit: CloudConfig,
    source: str,
    target: str,
) -> tuple[str, str, str]:
    print("Source:", source)
    print("Target:", target)
    if source.startswith(":"):
        if ES in target:
            raise NotImplementedError("Not Implemented here yet.")
        default_cloud = read_stackops_config_string("default_rclone_config")
        console.print(Panel(f"⚠️  No cloud name specified for source. Using default cloud: {default_cloud}", width=150, border_style="yellow"))
        source = default_cloud + ":" + source[1:]
    if target.startswith(":"):
        if ES in source:
            raise NotImplementedError("Not Implemented here yet.")
        default_cloud = read_stackops_config_string("default_rclone_config")
        console.print(Panel(f"⚠️  No cloud name specified for target. Using default cloud: {default_cloud}", width=150, border_style="yellow"))
        target = default_cloud + ":" + target[1:]
        print("target mutated to:", target, f"because of default cloud being {default_cloud}")

    if ":" in source and (source[1] != ":" if len(source) > 1 else True):  # avoid the deceptive case of "C:/"
        source_parts: list[str] = source.split(":")
        cloud = source_parts[0]
        if len(source_parts) > 1 and source_parts[1] == ES:  # the source path is to be inferred from target.
            assert ES not in target, f"You can't use expand symbol `{ES}` in both source and target. Cyclical inference dependency arised."
            target_obj = my_abs(target)
            remote_path = get_remote_path(
                local_path=target_obj,
                os_specific=cloud_config_explicit["os_specific"],
                root=cloud_config_explicit["root"],
                rel2home=cloud_config_explicit["rel2home"],
                strict=False,
            )
            source = f"{cloud}:{remote_path.as_posix()}"
        elif target == ES:  # target path is to be inferred from source.
            raise NotImplementedError("There is no .get_local_path method yet")
        else:  # source path is mentioned, target? maybe.
            _ = my_abs(target)
        if cloud_config_explicit["zip"] and not source.endswith(".zip"):
            source += ".zip"
        if cloud_config_explicit["encrypt"] and not source.endswith(".gpg"):
            source += ".gpg"
    elif ":" in target and (target[1] != ":" if len(target) > 1 else True):  # avoid the case of "C:/"
        target_parts: list[str] = target.split(":")
        cloud = target.split(":")[0]
        if len(target_parts) > 1 and target_parts[1] == ES:  # the target path is to be inferred from source.
            assert ES not in source, "You can't use $ in both source and target. Cyclical inference dependency arised."
            source_obj = my_abs(source)
            remote_path = get_remote_path(
                local_path=source_obj,
                os_specific=cloud_config_explicit["os_specific"],
                root=cloud_config_explicit["root"],
                rel2home=cloud_config_explicit["rel2home"],
                strict=False,
            )
            target = f"{cloud}:{remote_path.as_posix()}"
        elif source == ES:
            raise NotImplementedError("There is no .get_local_path method yet")
        else:  # target path is mentioned, source? maybe.
            target = str(target)
            _ = my_abs(source)
        if cloud_config_explicit["zip"] and not target.endswith(".zip"):
            target += ".zip"
        if cloud_config_explicit["encrypt"] and not target.endswith(".gpg"):
            target += ".gpg"
    else:
        console.print(
            Panel(
                "❌ ERROR: Invalid path configuration\nEither source or target must be a remote path (i.e. machine:path)",
                title="[bold red]Error[/bold red]",
                border_style="red",
            )
        )
        raise ValueError(f"Either source or target must be a remote path (i.e. machine:path)\nGot: source: `{source}`, target: `{target}`")
    console.print(Panel("🔍 Path resolution complete", title="[bold blue]Resolution[/bold blue]", border_style="blue"))
    pprint({"cloud": cloud, "source": str(source), "target": str(target)}, "CLI Resolution")
    return cloud, str(source), str(target)
