from abc import ABC, abstractmethod
from dataclasses import dataclass

import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings


@dataclass
class EmailMessage:
    """Email message data class"""

    to: str
    subject: str
    body_html: str
    body_text: str


class EmailService(ABC):
    """Abstract base class for email services"""

    @abstractmethod
    async def send_email(self, message: EmailMessage) -> bool:
        """Send an email"""
        pass


class ConsoleEmailService(EmailService):
    """
    Development email service that prints emails to console.
    Use this for local development and testing.
    """

    async def send_email(self, message: EmailMessage) -> bool:
        """Print email to console instead of sending"""
        print("\n" + "=" * 80)
        print("📧 EMAIL (Console Output - Development Mode)")
        print("=" * 80)
        print(f"To: {message.to}")
        print(f"Subject: {message.subject}")
        print("-" * 80)
        print("Text Body:")
        print(message.body_text)
        print("=" * 80 + "\n")
        return True


class SMTPEmailService(EmailService):
    """
    Production email service that sends emails via SMTP.
    Supports Gmail, SendGrid, and other SMTP providers.
    """

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
        """Send email via SMTP"""
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = message.subject
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = message.to

            # Attach text and HTML parts
            part1 = MIMEText(message.body_text, "plain")
            part2 = MIMEText(message.body_html, "html")
            msg.attach(part1)
            msg.attach(part2)

            # Send via SMTP
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
    """
    Factory function to get the appropriate email service.
    Returns ConsoleEmailService for development, SMTPEmailService for production.
    """
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


def build_password_reset_email(name: str, email: str, token: str) -> EmailMessage:
    """
    Build password reset email with link.

    Args:
        name: User's name
        email: User's email
        token: Password reset token (raw, not hashed)

    Returns:
        EmailMessage ready to send
    """
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2 style="color: #4CAF50;">Reset hasła - Efektywniejsi</h2>
        <p>Cześć {name},</p>
        <p>Otrzymaliśmy prośbę o reset hasła do Twojego konta.</p>
        <p>Kliknij poniższy link, aby ustawić nowe hasło:</p>
        <p style="margin: 20px 0;">
            <a href="{reset_url}"
               style="background-color: #4CAF50; color: white; padding: 12px 24px;
                      text-decoration: none; border-radius: 4px; display: inline-block;">
                Zresetuj hasło
            </a>
        </p>
        <p><strong>Link wygasa za 1 godzinę.</strong></p>
        <p>Jeśli nie prosiłeś o reset hasła, zignoruj tę wiadomość.</p>
        <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
        <p style="font-size: 12px; color: #999;">
            © 2026 Efektywniejsi. Wszystkie prawa zastrzeżone.
        </p>
    </body>
    </html>
    """

    text_body = f"""
Reset hasła - Efektywniejsi

Cześć {name},

Otrzymaliśmy prośbę o reset hasła do Twojego konta.

Użyj poniższego linku, aby ustawić nowe hasło:
{reset_url}

Link wygasa za 1 godzinę.

Jeśli nie prosiłeś o reset hasła, zignoruj tę wiadomość.

---
© 2026 Efektywniejsi. Wszystkie prawa zastrzeżone.
    """

    return EmailMessage(
        to=email,
        subject="Reset hasła - Efektywniejsi",
        body_html=html_body,
        body_text=text_body,
    )


def build_welcome_email(name: str, email: str, temp_password: str) -> EmailMessage:
    """
    Build welcome email for admin-created users.

    Args:
        name: User's name
        email: User's email
        temp_password: Temporary password

    Returns:
        EmailMessage ready to send
    """
    login_url = f"{settings.FRONTEND_URL}/login"

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2 style="color: #4CAF50;">Witaj w Efektywniejsi!</h2>
        <p>Cześć {name},</p>
        <p>Twoje konto zostało utworzone. Oto Twoje dane logowania:</p>
        <div style="background-color: #f5f5f5; padding: 15px; border-radius: 4px; margin: 20px 0;">
            <p><strong>Email:</strong> {email}</p>
            <p><strong>Hasło tymczasowe:</strong> {temp_password}</p>
        </div>
        <p>
            <a href="{login_url}"
               style="background-color: #4CAF50; color: white; padding: 12px 24px;
                      text-decoration: none; border-radius: 4px; display: inline-block;">
                Zaloguj się teraz
            </a>
        </p>
        <p><strong>Ważne:</strong> Zmień hasło po pierwszym logowaniu.</p>
        <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
        <p style="font-size: 12px; color: #999;">
            © 2026 Efektywniejsi. Wszystkie prawa zastrzeżone.
        </p>
    </body>
    </html>
    """

    text_body = f"""
Witaj w Efektywniejsi!

Cześć {name},

Twoje konto zostało utworzone. Oto Twoje dane logowania:

Email: {email}
Hasło tymczasowe: {temp_password}

Zaloguj się: {login_url}

Ważne: Zmień hasło po pierwszym logowaniu.

---
© 2026 Efektywniejsi. Wszystkie prawa zastrzeżone.
    """

    return EmailMessage(
        to=email,
        subject="Witaj w Efektywniejsi",
        body_html=html_body,
        body_text=text_body,
    )
