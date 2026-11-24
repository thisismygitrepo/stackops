from starlette.routing import Route

from stackops.scripts.python.helpers.helpers_webui.security_cloud_routes import security_cloud_routes
from stackops.scripts.python.helpers.helpers_webui.security_locker_routes import security_locker_routes
from stackops.scripts.python.helpers.helpers_webui.security_scan_routes import security_scan_routes


# What the Security page's purpose-built views read and change, all under /api/security/: the saved scans to install from or export
# (/scans/), the cloud a file is uploaded to and the Google Drive link one is downloaded from (/cloud/), and encrypting and decrypting (/locker/).
def security_routes() -> list[Route]:
    return [*security_scan_routes(), *security_cloud_routes(), *security_locker_routes()]
