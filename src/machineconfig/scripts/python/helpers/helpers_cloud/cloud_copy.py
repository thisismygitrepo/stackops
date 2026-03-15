"""
CC
"""

from machineconfig.utils.ve import CLOUD, read_default_cloud_config

from tenacity import retry, stop_after_attempt, wait_chain, wait_fixed


defaults = read_default_cloud_config()


@retry(stop=stop_after_attempt(3), wait=wait_chain(wait_fixed(1), wait_fixed(4), wait_fixed(9)))
def get_securely_shared_file(url: str | None, folder: str | None) -> None:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress
    import getpass
    import os
    from machineconfig.utils.path_extended import PathExtended
    console = Console()
    console.print(Panel("🚀 Secure File Downloader", title="[bold blue]Downloader[/bold blue]", border_style="blue"))
    folder_obj = PathExtended.cwd() if folder is None else PathExtended(folder)
    print(f"📂 Target folder: {folder_obj}")

    if os.environ.get("DECRYPTION_PASSWORD") is not None:
        print("🔑 Using password from environment variables")
        pwd = str(os.environ.get("DECRYPTION_PASSWORD"))
    else:
        pwd = getpass.getpass(prompt="🔑 Enter decryption password: ")

    if url is None:
        if os.environ.get("SHARE_URL") is not None:
            url = os.environ.get("SHARE_URL")
            assert url is not None
            print("🔗 Using URL from environment variables")
        else:
            url = input("🔗 Enter share URL: ")

    console.print(Panel("📡 Downloading from URL...", title="[bold blue]Download[/bold blue]", border_style="blue"))
    with Progress(transient=True) as progress:
        _task = progress.add_task("Downloading... ", total=None)
        url_obj = PathExtended(url).download(folder=folder_obj)

    console.print(Panel(f"📥 Downloaded file: {url_obj}", title="[bold green]Success[/bold green]", border_style="green"))

    console.print(Panel("🔐 Decrypting and extracting...", title="[bold blue]Processing[/bold blue]", border_style="blue"))
    with Progress(transient=True) as progress:
        _task = progress.add_task("Decrypting... ", total=None)
        tmp_folder = PathExtended.tmpdir(prefix="tmp_unzip")
        try:
            res = url_obj.decrypt(pwd=pwd, inplace=True).unzip(inplace=True, folder=tmp_folder)
            for x in res.glob("*"):
                x.move(folder=folder_obj, overwrite=True)
        finally:
            # Clean up temporary folder
            if tmp_folder.exists():
                tmp_folder.delete()

def main(
    source: str,
    target: str,
    overwrite: bool,
    share: bool,
    rel2home: bool,
    root: str,
    key: str | None,
    pwd: str | None,
    encrypt: bool,
    zip_: bool,
    os_specific: bool,
    config: str | None,
) -> None:
    """📤 Upload or 📥 Download files/folders to/from cloud storage services like Google Drive, Dropbox, OneDrive, etc."""
    from rich.console import Console
    from rich.panel import Panel
    from machineconfig.utils.path_extended import PathExtended
    from machineconfig.scripts.python.helpers.helpers_cloud.helpers2 import parse_cloud_source_target
    console = Console()
    console.print(Panel("☁️  Cloud Copy Utility", title="[bold blue]Cloud Copy[/bold blue]", border_style="blue", width=152))
    cloud_config_explicit = CLOUD(
        cloud="",
        overwrite=overwrite,
        share=share,
        rel2home=rel2home,
        root=root,
        key=key,
        pwd=pwd,
        encrypt=encrypt,
        zip=zip_,
        os_specific=os_specific,
    )

    if config == "ss" and (source.startswith("http") or source.startswith("bit.ly")):
        console.print(Panel("🔒 Detected secure share link", title="[bold yellow]Warning[/bold yellow]", border_style="yellow"))
        if source.startswith("https://drive.google.com/open?id="):
            file_id = source.split("https://drive.google.com/open?id=")[1]
            if file_id:  # Ensure we actually extracted an ID
                source = f"https://drive.google.com/uc?export=download&id={file_id}"
                print("🔄 Converting Google Drive link to direct download URL")
            else:
                console.print(Panel("❌ Invalid Google Drive link format", title="[bold red]Error[/bold red]", border_style="red"))
                raise SystemExit(1)
        get_securely_shared_file(url=source, folder=target)
        return

    console.print(Panel("🔍 Parsing source and target paths...", title="[bold blue]Info[/bold blue]", border_style="blue"))
    cloud, source, target = parse_cloud_source_target(
        cloud_config_explicit=cloud_config_explicit,
        cloud_config_defaults=defaults,
        cloud_config_name=config,
        source=source,
        target=target,
    )
    if cloud_config_explicit["key"] is not None:
        console.print(Panel("❌ Key-based encryption is not supported yet", title="[bold red]Error[/bold red]", border_style="red"))
        raise SystemExit(1)
    if cloud in source:
        console.print(Panel(f"📥 DOWNLOADING FROM CLOUD\n☁️  Cloud: {cloud}\n📂 Source: {source.replace(cloud + ':', '')}\n🎯 Target: {target}", title="[bold blue]Download[/bold blue]", border_style="blue", width=152))
        PathExtended(target).from_cloud(
            cloud=cloud,
            remotepath=source.replace(cloud + ":", ""),
            unzip=cloud_config_explicit["zip"],
            decrypt=cloud_config_explicit["encrypt"],
            pwd=cloud_config_explicit["pwd"],
            overwrite=cloud_config_explicit["overwrite"],
            rel2home=cloud_config_explicit["rel2home"],
            os_specific=cloud_config_explicit["os_specific"],
            root=cloud_config_explicit["root"],
            strict=False,
        )
        console.print(Panel("✅ Download completed successfully", title="[bold green]Success[/bold green]", border_style="green", width=152))

    elif cloud in target:
        console.print(Panel(f"📤 UPLOADING TO CLOUD\n☁️  Cloud: {cloud}\n📂 Source: {source}\n🎯 Target: {target.replace(cloud + ':', '')}", title="[bold blue]Upload[/bold blue]", border_style="blue", width=152))

        res = PathExtended(source).to_cloud(
            cloud=cloud,
            remotepath=target.replace(cloud + ":", ""),
            zip=cloud_config_explicit["zip"],
            encrypt=cloud_config_explicit["encrypt"],
            pwd=cloud_config_explicit["pwd"],
            rel2home=cloud_config_explicit["rel2home"],
            root=cloud_config_explicit["root"],
            os_specific=cloud_config_explicit["os_specific"],
            strict=False,
            share=cloud_config_explicit["share"],
        )
        console.print(Panel("✅ Upload completed successfully", title="[bold green]Success[/bold green]", border_style="green", width=152))

        if cloud_config_explicit["share"]:
            fname = f".share_url_{cloud}"
            if PathExtended(source).is_dir():
                share_url_path = PathExtended(source).joinpath(fname)
            else:
                share_url_path = PathExtended(source).with_suffix(fname)
            share_url_path.write_text(res.as_url_str(), encoding="utf-8")
            console.print(Panel(f"🔗 SHARE URL GENERATED\n📝 URL file: {share_url_path}\n🌍 {res.as_url_str()}", title="[bold blue]Share[/bold blue]", border_style="blue", width=152))
    else:
        console.print(Panel(f"❌ ERROR: Cloud '{cloud}' not found in source or target", title="[bold red]Error[/bold red]", border_style="red", width=152))
        raise SystemExit(1)
