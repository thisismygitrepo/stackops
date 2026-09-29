from stackops.scripts.python.helpers.helpers_window.window_models import WindowAction


ACTION_DESCRIPTIONS: dict[WindowAction, str] = {
    "minimize": "Minimize the selected window.",
    "maximize": "Expand the selected window to the usable screen area.",
    "unminimize": "Bring a minimized window back onto the desktop.",
    "focus": "Bring the selected window to the foreground, unminimizing it if needed.",
    "close": "Request that the window close. The application may ask to save changes.",
}
AX_TIMEOUT_SECONDS = 3.0
