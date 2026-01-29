from abc import ABC, abstractmethod
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from app.core.config import settings

# Brand colors
_VIOLET = "#A855F7"
_CYAN = "#06B6D4"
_BG_DARK = "#0F172A"
_CARD_BG = "#1E293B"
_TEXT_LIGHT = "#F0F9FF"
_TEXT_MUTED = "#94A3B8"
_BORDER = "#334155"


@dataclass
class EmailMessage:
    to: str
    subject: str
    body_html: str
    body_text: str


class EmailService(ABC):
    @abstractmethod
    async def send_email(self, message: EmailMessage) -> bool:
        pass


class ConsoleEmailService(EmailService):
    async def send_email(self, message: EmailMessage) -> bool:
        print("\n" + "=" * 80)
        print("EMAIL (Console Output - Development Mode)")
        print("=" * 80)
        print(f"To: {message.to}")
        print(f"Subject: {message.subject}")
        print("-" * 80)
        print("Text Body:")
        print(message.body_text)
        print("=" * 80 + "\n")
        return True


class SMTPEmailService(EmailService):
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_email: str,
        from_name: str,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.from_name = from_name

    async def send_email(self, message: EmailMessage) -> bool:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = message.subject
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = message.to

            part1 = MIMEText(message.body_text, "plain")
            part2 = MIMEText(message.body_html, "html")
            msg.attach(part1)
            msg.attach(part2)

            await aiosmtplib.send(
                msg,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.username,
                password=self.password,
                start_tls=True,
            )
            return True
        except Exception as e:
            print(f"Failed to send email: {e}")
            return False


def get_email_service() -> EmailService:
    if settings.EMAIL_BACKEND == "smtp":
        return SMTPEmailService(
            smtp_host=settings.SMTP_HOST,
            smtp_port=settings.SMTP_PORT,
            username=settings.SMTP_USERNAME,
            password=settings.SMTP_PASSWORD,
            from_email=settings.SMTP_FROM_EMAIL,
            from_name=settings.SMTP_FROM_NAME,
        )
    return ConsoleEmailService()


def _wrap_html(inner: str) -> str:
    """Wrap email content in the branded dark template."""
    return f"""\
<html>
<body style="margin: 0; padding: 0; background-color: {_BG_DARK}; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color: {_BG_DARK}; padding: 32px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="max-width: 600px; width: 100%;">
          <!-- Logo -->
          <tr>
            <td align="center" style="padding: 0 0 32px 0;">
              <img src="{settings.FRONTEND_URL}/logo/efektywniejsi-logo-white.png"
                   alt="Efektywniejsi" height="36"
                   style="height: 36px; width: auto;" />
            </td>
          </tr>
          <!-- Card -->
          <tr>
            <td style="background-color: {_CARD_BG}; border: 1px solid {_BORDER}; border-radius: 12px; padding: 40px 36px;">
              {inner}
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td align="center" style="padding: 24px 0 0 0;">
              <p style="margin: 0; font-size: 12px; color: {_TEXT_MUTED}; line-height: 1.5;">
                &copy; 2026 Efektywniejsi. Wszystkie prawa zastrzeżone.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def build_password_reset_email(name: str, email: str, token: str) -> EmailMessage:
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"

    inner = f"""\
<h2 style="margin: 0 0 24px 0; font-size: 22px; font-weight: 700; color: {_TEXT_LIGHT};">
  Reset hasła
</h2>
<p style="margin: 0 0 16px 0; font-size: 15px; color: {_TEXT_MUTED}; line-height: 1.6;">
  Cześć {name},
</p>
<p style="margin: 0 0 20px 0; font-size: 15px; color: {_TEXT_MUTED}; line-height: 1.6;">
  Otrzymaliśmy prośbę o reset hasła do Twojego konta.
  Kliknij poniższy przycisk, aby ustawić nowe hasło:
</p>
<table cellpadding="0" cellspacing="0" style="margin: 0 0 24px 0;">
  <tr>
    <td style="border-radius: 8px; background: linear-gradient(135deg, {_VIOLET}, {_CYAN});">
      <a href="{reset_url}"
         style="display: inline-block; padding: 12px 28px; font-size: 14px; font-weight: 600;
                color: #ffffff; text-decoration: none; border-radius: 8px;">
        Zresetuj hasło
      </a>
    </td>
  </tr>
</table>
<p style="margin: 0 0 8px 0; font-size: 14px; color: {_TEXT_LIGHT}; font-weight: 600;">
  Link wygasa za 1 godzinę.
</p>
<p style="margin: 0; font-size: 14px; color: {_TEXT_MUTED}; line-height: 1.6;">
  Jeśli nie prosiłeś o reset hasła, zignoruj tę wiadomość.
</p>"""

    text_body = f"""\
Reset hasła - Efektywniejsi

Cześć {name},

Otrzymaliśmy prośbę o reset hasła do Twojego konta.

Użyj poniższego linku, aby ustawić nowe hasło:
{reset_url}

Link wygasa za 1 godzinę.

Jeśli nie prosiłeś o reset hasła, zignoruj tę wiadomość.

---
© 2026 Efektywniejsi. Wszystkie prawa zastrzeżone."""

    return EmailMessage(
        to=email,
        subject="Reset hasła - Efektywniejsi",
        body_html=_wrap_html(inner),
        body_text=text_body,
    )


def build_welcome_email(name: str, email: str, temp_password: str) -> EmailMessage:
    login_url = f"{settings.FRONTEND_URL}/login"

    inner = f"""\
<h2 style="margin: 0 0 24px 0; font-size: 22px; font-weight: 700; color: {_TEXT_LIGHT};">
  Witaj w Efektywniejsi!
</h2>
<p style="margin: 0 0 16px 0; font-size: 15px; color: {_TEXT_MUTED}; line-height: 1.6;">
  Cześć {name},
</p>
<p style="margin: 0 0 20px 0; font-size: 15px; color: {_TEXT_MUTED}; line-height: 1.6;">
  Twoje konto zostało utworzone. Oto Twoje dane logowania:
</p>
<div style="background-color: {_BG_DARK}; border: 1px solid {_BORDER}; border-radius: 8px; padding: 16px 20px; margin: 0 0 24px 0;">
  <p style="margin: 0 0 8px 0; font-size: 14px; color: {_TEXT_MUTED};">
    <strong style="color: {_TEXT_LIGHT};">Email:</strong> {email}
  </p>
  <p style="margin: 0; font-size: 14px; color: {_TEXT_MUTED};">
    <strong style="color: {_TEXT_LIGHT};">Hasło tymczasowe:</strong> {temp_password}
  </p>
</div>
<table cellpadding="0" cellspacing="0" style="margin: 0 0 24px 0;">
  <tr>
    <td style="border-radius: 8px; background: linear-gradient(135deg, {_VIOLET}, {_CYAN});">
      <a href="{login_url}"
         style="display: inline-block; padding: 12px 28px; font-size: 14px; font-weight: 600;
                color: #ffffff; text-decoration: none; border-radius: 8px;">
        Zaloguj się teraz
      </a>
    </td>
  </tr>
</table>
<p style="margin: 0; font-size: 14px; color: {_TEXT_LIGHT}; font-weight: 600;">
  Ważne: Zmień hasło po pierwszym logowaniu.
</p>"""

    text_body = f"""\
Witaj w Efektywniejsi!

Cześć {name},

Twoje konto zostało utworzone. Oto Twoje dane logowania:

Email: {email}
Hasło tymczasowe: {temp_password}

Zaloguj się: {login_url}

Ważne: Zmień hasło po pierwszym logowaniu.

---
© 2026 Efektywniejsi. Wszystkie prawa zastrzeżone."""

    return EmailMessage(
        to=email,
        subject="Witaj w Efektywniejsi",
        body_html=_wrap_html(inner),
        body_text=text_body,
    )
