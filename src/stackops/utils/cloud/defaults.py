from typing import TypedDict

from stackops.utils.cloud.encryption import EncryptionMode


class CloudConfig(TypedDict, total=True):
    cloud: str
    root: str
    rel2home: bool
    pwd: str | None
    encrypt: bool
    encryption: EncryptionMode | None
    os_specific: bool
    zip: bool
    share: bool
    overwrite: bool


def read_default_cloud_config() -> CloudConfig:
    return {
        "cloud": "mycloud101",
        "root": "myhome",
        "rel2home": False,
        "pwd": None,
        "encrypt": False,
        "encryption": None,
        "os_specific": False,
        "zip": False,
        "share": False,
        "overwrite": False,
    }
