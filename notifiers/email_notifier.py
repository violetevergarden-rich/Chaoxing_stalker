import smtplib
import html as html_mod
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

from notifiers import Notifier


class EmailNotifier(Notifier):
    """SMTP 邮件通知"""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        use_ssl: bool,
        sender: str,
        auth_code: str,
        recipients: list[str],
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.use_ssl = use_ssl
        self.sender = sender
        self.auth_code = auth_code
        self.recipients = recipients if isinstance(recipients, list) else [recipients]

    @classmethod
    def from_config(cls, config: dict) -> "EmailNotifier":
        return cls(
            smtp_host=config["smtp_host"],
            smtp_port=config["smtp_port"],
            use_ssl=config.get("use_ssl", True),
            sender=config["sender"],
            auth_code=config["authorization_code"],
            recipients=config["recipients"],
        )

    def send(self, subject: str, message: str) -> bool:
        msg = MIMEMultipart("alternative")
        msg["From"] = self.sender
        msg["To"] = ", ".join(self.recipients)
        msg["Subject"] = Header(subject, "utf-8")
        msg.attach(MIMEText(message, "plain", "utf-8"))
        msg.attach(MIMEText(self._plain_to_html(message), "html", "utf-8"))

        try:
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=15)
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=15)
                server.starttls()
            server.login(self.sender, self.auth_code)
            server.sendmail(self.sender, self.recipients, msg.as_string())
            server.quit()
            return True
        except (smtplib.SMTPException, OSError) as e:
            print(f"[ERROR] 邮件发送失败: {e}")
            return False

    @staticmethod
    def _plain_to_html(text: str) -> str:
        escaped = html_mod.escape(text)
        return f"<html><body><pre style='font-size:14px;font-family:monospace;'>{escaped}</pre></body></html>"
