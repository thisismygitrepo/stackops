"""Notifications Module"""

import json
from pathlib import Path
import smtplib
import imaplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any, Union
from rich.console import Console
from rich.markdown import Markdown


def download_to_memory(path: Path, allow_redirects: bool = True, timeout: float | None = None, params: Any = None) -> "Any":
    import requests
    return requests.get(
        path.as_posix().replace("https:/", "https://").replace("http:/", "http://"), allow_redirects=allow_redirects, timeout=timeout, params=params
    )  # Alternative: from urllib import request; request.urlopen(url).read().decode('utf-8').


def get_github_markdown_css() -> str:
    pp = r"https://raw.githubusercontent.com/sindresorhus/github-markdown-css/main/github-markdown-dark.css"
    return download_to_memory(Path(pp)).text


def md2html(body: str) -> str:
    """Convert markdown to HTML using Rich library."""
    # Use Rich's HTML export functionality to convert markdown to HTML
    console = Console(record=True, width=120)
    markdown_obj = Markdown(body)
    console.print(markdown_obj)
    html_output = console.export_html(inline_styles=True)

    gh_style = """
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
        h1, h2, h3, h4, h5, h6 { color: #0366d6; }
        code { background-color: #f6f8fa; padding: 2px 4px; border-radius: 3px; }
        pre { background-color: #f6f8fa; padding: 16px; border-radius: 6px; overflow: auto; }
        """

    return f"""
<!DOCTYPE html>
<html>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
{gh_style}
    .markdown-body {{
        box-sizing: border-box;
        min-width: 200px;
        max-width: 1350px;
        margin: 0 auto;
        padding: 45px;
        line-height: 1.8;
    }}
    @media (max-width: 767px) {{.markdown-body {{padding: 15px;}}
    }}
</style>
<body>
<div class="markdown-body">
{html_output}
</div>
</body>
</html>"""


EMAIL_SECRET_KEYS: tuple[str, str, str, str, str] = ("email_add", "password", "encryption", "smtp_host", "smtp_port")


class Email:
    def __init__(self, config_name: str):
        from stackops.secrets import Login, render_secret_value, search_logins
        from stackops.utils.source_of_truth import SECRETS_DOFILE
        secrets = search_logins(path=SECRETS_DOFILE, login_name=config_name, keys=EMAIL_SECRET_KEYS)
        if len(secrets) == 0:
            expected_entry: Login = {
                "name": config_name,
                "secrets": [
                    {
                        "name": "smtp",
                        "tags": [],
                        "scopes": [],
                        "keyValues": {
                            "email_add": "you@example.com",
                            "password": "<email-password-or-app-password>",
                            "encryption": "tls",
                            "smtp_host": "smtp.example.com",
                            "smtp_port": "587",
                        },
                    }
                ],
            }
            raise ValueError(
                f"No email secrets found for config_name: {config_name}\n"
                f"Expected {SECRETS_DOFILE} to contain a login entry shaped like:\n"
                + json.dumps(expected_entry, indent=2)
            )
        if len(secrets) > 1:
            raise ValueError(f"Multiple email secrets found for config_name: {config_name}. Please ensure config_name is unique.")
        config = secrets[0]["secrets"][0]["keyValues"]
        email_add = config["email_add"]
        if not isinstance(email_add, str):
            raise TypeError(f"Secret value at {config_name}.email_add must be a string.")
        password = config["password"]
        if not isinstance(password, str):
            raise TypeError(f"Secret value at {config_name}.password must be a string.")
        encryption = config["encryption"]
        if not isinstance(encryption, str):
            raise TypeError(f"Secret value at {config_name}.encryption must be a string.")
        smtp_host = config["smtp_host"]
        if not isinstance(smtp_host, str):
            raise TypeError(f"Secret value at {config_name}.smtp_host must be a string.")
        self.email_add = email_add
        encryption_name = encryption.lower()
        smtp_port = int(render_secret_value(config["smtp_port"]))
        from smtplib import SMTP_SSL, SMTP
        self.server: Union[SMTP_SSL, SMTP]
        if encryption_name == "ssl":
            self.server = smtplib.SMTP_SSL(host=smtp_host, port=smtp_port)
        elif encryption_name == "tls":
            self.server = smtplib.SMTP(host=smtp_host, port=smtp_port)
        self.server.login(self.email_add, password=password)

    def send_message(self, to: str, subject: str, body: str, txt_to_html: bool = True, attachments: list[Any] | None = None):
        _ = attachments
        body += "\n\nThis is an automated email sent via stackops.comms script."
        # msg = message.EmailMessage()
        msg = MIMEMultipart("alternative")
        msg["subject"] = subject
        msg["From"] = self.email_add
        msg["To"] = to
        # msg['Content-Type'] = "text/html"
        # msg.set_content(body)

        # <link rel="stylesheet" href="github-markdown.css">
        # <link type="text/css" rel="stylesheet" href="https://raw.githubusercontent.com/sindresorhus/github-markdown-css/main/github-markdown-dark.css" />

        if txt_to_html:
            body = md2html(body=body)
        msg.attach(MIMEText(body, "html"))
        # if attachments is None: attachments = []  # see: https://fedingo.com/how-to-send-html-mail-with-attachment-using-python/
        # for attachment in attachmenthrs: msg.attach(attachment.read_bytes(), filename=attachment.stem, maintype="image", subtype=attachment.suffix)
        # for attachment in attachments: msg.attach(attachment.read_bytes(), filename=attachment.stem, maintype="application", subtype="octet-stream")

        self.server.send_message(msg)

    @staticmethod
    def manage_folders(email_add: str, pwd: str):
        server = imaplib.IMAP4()
        server.starttls()
        server.login(email_add, password=pwd)

    def send_email(self, to_addrs: str, msg: str):
        return self.server.sendmail(from_addr=self.email_add, to_addrs=to_addrs, msg=msg)

    def close(self):
        self.server.quit()  # Closing is vital as many servers do not allow mutiple connections.

    @staticmethod
    def send_and_close(config_name: str, to: str, subject: str, body: str) -> Any:
        tmp = Email(config_name=config_name)
        tmp.send_message(to=to, subject=subject, body=body)
        tmp.close()

    # @staticmethod
    # def send_m365(to: list[str], subject: str, body: str | None, body_file: str | None, body_content_type: Literal["HTML", "Text"], attachments: list[Path] | None = None) -> None:
    #     if body_file is not None:
    #         assert body is None, "You cannot pass both body and body_file."
    #         body_file_path = Path(body_file)
    #         assert body_file_path.exists(), f"File not found: {body_file_path}"
    #     else:
    #         body_file_path = None
    #         assert body is not None, "You must pass either body or body_file."

    #     to_str = ",".join(to)
    #     attachments_str = " ".join([f"--attachment {str(p)}" for p in attachments]) if attachments is not None else ""

    #     if body_file is not None:
    #         body_arg = f"--bodyContents @{body_file_path}"
    #     else:
    #         body_arg = f'"{body}"'
    #     cmd = f"""m365 outlook mail send --verbose --saveToSentItems --importance normal --bodyContentType {body_content_type} --bodyContents {body_arg} --subject "{subject}" --to {to_str} {attachments_str}"""
    #     response = Terminal().run(cmd, shell="powershell")
    #     response.print(desc="Email sending response")



if __name__ == "__main__":
    pass
