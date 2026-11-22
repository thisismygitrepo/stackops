import secrets

from starlette.datastructures import MutableHeaders
from starlette.requests import HTTPConnection
from starlette.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from stackops.scripts.python.helpers.helpers_webui.constants import APP_CONTENT_SECURITY_POLICY, REPORT_CONTENT_SECURITY_POLICY

LOCKED_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>StackOps · access link needed</title>
<style>
:root { color-scheme: light dark; }
body { margin: 0; min-height: 100vh; display: grid; place-items: center; font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 440px; padding: 32px; }
h1 { margin: 0 0 8px; font-size: 20px; }
p { margin: 0 0 8px; opacity: 0.75; }
code { font: 13px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
</style>
</head>
<body>
<main>
<h1>This session needs its access link</h1>
<p>Open the full URL that <code>stackops webui</code> printed in your terminal. It carries the access token for this server.</p>
<p>The link changes every time the server starts.</p>
</main>
</body>
</html>
"""


def guard_access(app: ASGIApp, token: str, cookie_name: str) -> ASGIApp:
    expected = token.encode()

    async def guarded(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await app(scope, receive, send)
            return
        connection = HTTPConnection(scope)
        path: str = scope["path"]

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["Content-Security-Policy"] = REPORT_CONTENT_SECURITY_POLICY if path.startswith("/reports/") else APP_CONTENT_SECURITY_POLICY
                headers["X-Content-Type-Options"] = "nosniff"
                headers["Referrer-Policy"] = "no-referrer"
                if path.startswith(("/api/", "/reports/")) or path in ("/", "/dev"):
                    headers["Cache-Control"] = "no-store"
                elif path.startswith("/assets/"):
                    # Without this a browser keeps scripts and styles for a while unasked, and an updated server meets a page running old modules.
                    headers["Cache-Control"] = "no-cache"
            await send(message)

        # SameSite cookies ignore the port, so another page on this host could still send them; the Origin check is what stops that.
        origin = connection.headers.get("origin")
        origin_required = scope["type"] == "websocket" or scope["method"] not in ("GET", "HEAD")
        denial: Response | None = None
        if (origin is None and origin_required) or (origin is not None and origin != f"""http://{connection.headers.get("host", "")}"""):
            denial = PlainTextResponse("Cross-origin requests are not allowed.", status_code=403)
        else:
            signed_in = secrets.compare_digest(connection.cookies.get(cookie_name, "").encode(), expected)
            offered = connection.query_params.get("token") if scope["type"] == "http" and path == "/" else None
            if offered is not None and (signed_in or secrets.compare_digest(offered.encode(), expected)):
                # The redirect also runs for a browser that is already signed in, so the token never stays in the address bar or the history.
                denial = RedirectResponse("/", status_code=303)
                # A design choice: Lax, not Strict, so the link also works when clicked on a web page (webmail, a chat app, a terminal in the browser).
                # The cost: another site can open a GET route in the top window. No GET route changes anything, and that site cannot read the answer.
                denial.set_cookie(cookie_name, token, httponly=True, samesite="lax")
            elif not signed_in:
                denial = HTMLResponse(LOCKED_PAGE, status_code=401)
        if denial is None:
            await app(scope, receive, send_with_headers)
        elif scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008})
        else:
            await denial(scope, receive, send_with_headers)

    return guarded
