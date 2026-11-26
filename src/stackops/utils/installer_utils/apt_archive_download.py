import shlex
from collections.abc import Sequence

from stackops.utils.installer_utils.constants import APT_DOWNLOAD_PACKAGES_PER_JOB, APT_DOWNLOAD_PARALLEL_JOBS


# apt-get install fetches one archive at a time. This asks apt which archives the packages need, fetches them with several
# `apt-get download` at once (same sources, proxy and checksum verification), and moves them into apt's cache, where the
# following `apt-get install` finds them. It needs fresh package lists, so it goes between `apt-get update` and `apt-get install`.
def build_apt_parallel_download_command(packages: Sequence[str], privilege_prefix: tuple[str, ...]) -> str:
    if len(packages) == 0:
        raise ValueError("At least one package is required")
    list_archives = rf"""apt-get install -y --print-uris {shlex.join(packages)} | awk '{{print $2}}' | sed -nE 's/^([^_]+)_([^_]+)_([^_.]+)\.deb$/\1:\3=\2/p' | sed -e 's/%3a/:/g' -e 's/:all=/=/'"""
    fetch_archives = f"""xargs -r -P {APT_DOWNLOAD_PARALLEL_JOBS} -n {APT_DOWNLOAD_PACKAGES_PER_JOB} apt-get download -q"""
    # a system that has not installed anything yet has no cache directory
    make_cache = shlex.join((*privilege_prefix, "mkdir", "-p", "/var/cache/apt/archives"))
    move_to_cache = shlex.join((*privilege_prefix, "mv", "-t", "/var/cache/apt/archives"))
    return " && ".join(
        (
            '''apt_archives="$(mktemp -d)"''',
            # root's apt drops to the _apt user to download, which must own the directory it writes to
            '''{ [ "$(id -u)" != 0 ] || chown _apt "$apt_archives"; }''',
            f"""(cd "$apt_archives" && {list_archives} | {fetch_archives})""",
            make_cache,
            f"""find "$apt_archives" -name '*.deb' -exec {move_to_cache} {{}} +""",
            '''rm -rf "$apt_archives"''',
        )
    )
