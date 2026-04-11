from machineconfig.scripts.python.helpers.helpers_cloud.cloud_helpers import my_abs, find_cloud_config, get_secure_share_cloud_config
from machineconfig.utils.ve import CLOUD
from machineconfig.utils.io import read_ini
from machineconfig.utils.source_of_truth import DEFAULTS_PATH
from machineconfig.utils.accessories import pprint
from rich.console import Console
from rich.panel import Panel


ES = "^"  # chosen carefully to not mean anything on any shell. `$` was a bad choice.
console = Console()


def merge_cloud_config(cloud_config_base: CLOUD, cloud_config_explicit: CLOUD, cloud_config_defaults: CLOUD) -> CLOUD:
    merged: CLOUD = {
        "cloud": cloud_config_base["cloud"],
        "root": cloud_config_base["root"],
        "rel2home": cloud_config_base["rel2home"],
        "pwd": cloud_config_base["pwd"],
        "key": cloud_config_base["key"],
        "encrypt": cloud_config_base["encrypt"],
        "os_specific": cloud_config_base["os_specific"],
        "zip": cloud_config_base["zip"],
        "share": cloud_config_base["share"],
        "overwrite": cloud_config_base["overwrite"],
    }
    if cloud_config_explicit["cloud"] != cloud_config_defaults["cloud"]:
        merged["cloud"] = cloud_config_explicit["cloud"]
    if cloud_config_explicit["root"] != cloud_config_defaults["root"]:
        merged["root"] = cloud_config_explicit["root"]
    if cloud_config_explicit["rel2home"] != cloud_config_defaults["rel2home"]:
        merged["rel2home"] = cloud_config_explicit["rel2home"]
    if cloud_config_explicit["pwd"] != cloud_config_defaults["pwd"]:
        merged["pwd"] = cloud_config_explicit["pwd"]
    if cloud_config_explicit["key"] != cloud_config_defaults["key"]:
        merged["key"] = cloud_config_explicit["key"]
    if cloud_config_explicit["encrypt"] != cloud_config_defaults["encrypt"]:
        merged["encrypt"] = cloud_config_explicit["encrypt"]
    if cloud_config_explicit["os_specific"] != cloud_config_defaults["os_specific"]:
        merged["os_specific"] = cloud_config_explicit["os_specific"]
    if cloud_config_explicit["zip"] != cloud_config_defaults["zip"]:
        merged["zip"] = cloud_config_explicit["zip"]
    if cloud_config_explicit["share"] != cloud_config_defaults["share"]:
        merged["share"] = cloud_config_explicit["share"]
    if cloud_config_explicit["overwrite"] != cloud_config_defaults["overwrite"]:
        merged["overwrite"] = cloud_config_explicit["overwrite"]
    return merged


def parse_cloud_source_target(
    cloud_config_explicit: CLOUD, cloud_config_defaults: CLOUD, cloud_config_name: str | None, source: str, target: str
) -> tuple[str, str, str]:
    print("Source:", source)
    print("Target:", target)

    # Step 1: find the third config if any
    cloud_config_from_name: CLOUD | None = None
    if cloud_config_name is not None:
        if cloud_config_name == "ss":
            cloud_maybe: str | None = target.split(":")[0]
            if cloud_maybe == "":
                cloud_maybe = None
            print("cloud_maybe:", cloud_maybe)
            cloud_config_from_name = get_secure_share_cloud_config(interactive=True, cloud=cloud_maybe)
        else:
            config_path = my_abs(cloud_config_name)
            console.print(Panel(f"📄 Loading configuration from: {cloud_config_name}", width=150, border_style="blue"))
            if config_path.exists():
                cloud_config_from_name = find_cloud_config(config_path)
                if cloud_config_from_name is None:
                    raise FileNotFoundError(f"Configuration file at {cloud_config_name} has no [cloud] section.")
            else:
                raise FileNotFoundError(f"Configuration passed is not a valid known config name nor a valid config file path: {cloud_config_name}")

    else:
        cloud_config_from_name = None

    # step 2: solve for missing cloud names in source/target if any
    if source.startswith(":") and cloud_config_from_name is None:  # cloud name is omitted, needs to be inferred from config file.
        if ES in target:
            raise NotImplementedError("Not Implemented here yet.")
        target_local_path = my_abs(target)  # if source is remote, target must be local, against which we can search for .ve.yaml
        cloud_config_from_name = find_cloud_config(path=target_local_path)
        if cloud_config_from_name is None:  # last resort, use default cloud (user didn't pass cloud name, didn't pass config file)
            default_cloud: str = read_ini(DEFAULTS_PATH)["general"]["rclone_config_name"]
            console.print(Panel(f"⚠️  No cloud config found. Using default cloud: {default_cloud}", width=150, border_style="yellow"))
            source = default_cloud + ":" + source[1:]
        else:
            source = cloud_config_from_name["cloud"] + ":" + source[1:]
    if target.startswith(":"):  # default cloud name is omitted cloud_name:  # or ES in target
        if ES in source:
            raise NotImplementedError("Not Implemented here yet.")
        source_local_path = my_abs(source)
        if cloud_config_from_name is None:
            cloud_config_from_name = find_cloud_config(source_local_path)
        if cloud_config_from_name is None:
            default_cloud = read_ini(DEFAULTS_PATH)["general"]["rclone_config_name"]
            console.print(Panel(f"⚠️  No cloud config found. Using default cloud: {default_cloud}", width=150, border_style="yellow"))
            target = default_cloud + ":" + target[1:]
            print("target mutated to:", target, f"because of default cloud being {default_cloud}")
        else:
            target = cloud_config_from_name["cloud"] + ":" + target[1:]

    cloud_config_final: CLOUD
    if cloud_config_from_name is None:
        cloud_config_final = cloud_config_explicit
    else:
        cloud_config_final = merge_cloud_config(
            cloud_config_base=cloud_config_from_name,
            cloud_config_explicit=cloud_config_explicit,
            cloud_config_defaults=cloud_config_defaults,
        )

    if ":" in source and (source[1] != ":" if len(source) > 1 else True):  # avoid the deceptive case of "C:/"
        source_parts: list[str] = source.split(":")
        cloud = source_parts[0]
        if len(source_parts) > 1 and source_parts[1] == ES:  # the source path is to be inferred from target.
            assert ES not in target, f"You can't use expand symbol `{ES}` in both source and target. Cyclical inference dependency arised."
            target_obj = my_abs(target)
            from machineconfig.utils.path_extended import PathExtended

            remote_path = PathExtended(target_obj).get_remote_path(
                os_specific=cloud_config_final["os_specific"], root=cloud_config_final["root"], rel2home=cloud_config_final["rel2home"], strict=False
            )
            source = f"{cloud}:{remote_path.as_posix()}"
        elif target == ES:  # target path is to be inferred from source.
            raise NotImplementedError("There is no .get_local_path method yet")
        else:  # source path is mentioned, target? maybe.
            target_obj = my_abs(target)
        if cloud_config_final["zip"] and not source.endswith(".zip"):
            source += ".zip"
        if cloud_config_final["encrypt"] and not source.endswith(".gpg"):
            source += ".gpg"
    elif ":" in target and (target[1] != ":" if len(target) > 1 else True):  # avoid the case of "C:/"
        target_parts: list[str] = target.split(":")
        cloud = target.split(":")[0]
        if len(target_parts) > 1 and target_parts[1] == ES:  # the target path is to be inferred from source.
            assert ES not in source, "You can't use $ in both source and target. Cyclical inference dependency arised."
            source_obj = my_abs(source)
            from machineconfig.utils.path_extended import PathExtended

            remote_path = PathExtended(source_obj).get_remote_path(
                os_specific=cloud_config_final["os_specific"], root=cloud_config_final["root"], rel2home=cloud_config_final["rel2home"], strict=False
            )
            target = f"{cloud}:{remote_path.as_posix()}"
        elif source == ES:
            raise NotImplementedError("There is no .get_local_path method yet")
        else:  # target path is mentioned, source? maybe.
            target = str(target)
            source_obj = my_abs(source)
        if cloud_config_final["zip"] and not target.endswith(".zip"):
            target += ".zip"
        if cloud_config_final["encrypt"] and not target.endswith(".gpg"):
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
