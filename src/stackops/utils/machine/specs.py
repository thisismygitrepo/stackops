from typing import Literal, TypedDict, cast


MACHINE_SPECS_COMMAND_NAME = "get-machine-specs"


class MachineSpecs(TypedDict):
    system: Literal["Windows", "Linux", "Darwin"]
    distro: str
    home_dir: str
    hostname: str
    release: str
    version: str
    machine: str
    processor: str
    python_version: str
    user: str


def get_machine_specs() -> MachineSpecs:
    import platform
    import subprocess
    import socket
    import os
    from pathlib import Path

    from stackops.utils.code import get_uv_command

    uv_cmd = get_uv_command(platform=platform.system())
    command = f"""{uv_cmd} run --with distro python -c "import distro; print(distro.name(pretty=True))" """

    distro = "Unknown"
    try:
        distro_process = subprocess.run(command, shell=True, capture_output=True, text=True, check=False)
        detected_distro = distro_process.stdout.strip()
        if distro_process.returncode == 0 and detected_distro:
            distro = detected_distro
    except OSError:
        pass
    system = platform.system()
    if system not in {"Windows", "Linux", "Darwin"}:
        system = "Linux"
    specs: MachineSpecs = {
        "system": cast(Literal["Windows", "Linux", "Darwin"], system),
        "distro": distro,
        "home_dir": str(Path.home()),
        "hostname": socket.gethostname(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor() or "Unknown",
        "python_version": platform.python_version(),
        "user": os.getenv("USER") or os.getenv("USERNAME") or "Unknown",
    }
    return specs
