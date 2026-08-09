LOGIN_NAME = "onedrive"
SECRET_NAME = "oauth"
CLIENT_ID_KEY = "ONEDRIVE_CLIENT_ID"
REFRESH_TOKEN_KEY = "ONEDRIVE_REFRESH_TOKEN"

SCOPES: tuple[str, ...] = ("User.Read", "Files.ReadWrite", "offline_access")
SCOPE_TEXT = " ".join(SCOPES)

DEVICE_ENDPOINT = "https://login.microsoftonline.com/consumers/oauth2/v2.0/devicecode"
TOKEN_ENDPOINT = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
GRAPH_BASE = "https://graph.microsoft.com/v1.0"
REQUEST_TIMEOUT = 30
