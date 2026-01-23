"""
Email service for package-related emails.
"""

from app.auth.services.email_service import EmailMessage, get_email_service
from app.core.config import settings
from app.packages.models.enrollment import PackageEnrollment
from app.packages.models.order import Order


async def send_welcome_with_package_email(
    name: str,
    email: str,
    order: Order,
    enrollments: list[PackageEnrollment],
    reset_token: str,
) -> bool:
    """
    Send welcome email to new user with purchased packages and password setup link.

    Args:
        name: User's name
        email: User's email
        order: Order object
        enrollments: List of package enrollments
        reset_token: Raw password reset token (not hashed!)

    Returns:
        True if email sent successfully
    """
    email_service = get_email_service()
    message = _build_welcome_package_email(name, email, order, enrollments, reset_token)
    return await email_service.send_email(message)


async def send_purchase_confirmation_email(
    name: str,
    email: str,
    order: Order,
    enrollments: list[PackageEnrollment],
) -> bool:
    """
    Send purchase confirmation email to existing user.

    Args:
        name: User's name
        email: User's email
        order: Order object
        enrollments: List of package enrollments

    Returns:
        True if email sent successfully
    """
    email_service = get_email_service()
    message = _build_purchase_confirmation_email(name, email, order, enrollments)
    return await email_service.send_email(message)


def _build_welcome_package_email(
    name: str,
    email: str,
    order: Order,
    enrollments: list[PackageEnrollment],
    reset_token: str,
) -> EmailMessage:
    """Build welcome email with package list and password setup."""
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
    dashboard_url = f"{settings.FRONTEND_URL}/dashboard/packages"

    # Build package list
    package_list_html = "".join(
        [
            f'<li style="margin: 10px 0;">{enrollment.package.title}</li>'
            for enrollment in enrollments
        ]
    )
    package_list_text = "\n".join([f"  • {enrollment.package.title}" for enrollment in enrollments])

    # Format price (from grosz to PLN)
    total_pln = order.total / 100

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2 style="color: #4CAF50;">Witaj w Efektywniejsi! 🎉</h2>
        <p>Cześć {name},</p>
        <p>Dziękujemy za zakup! Twoje zamówienie <strong>{order.order_number}</strong>
        zostało zrealizowane.</p>

        <h3 style="color: #333; margin-top: 25px;">Zakupione pakiety:</h3>
        <ul style="line-height: 2;">
            {package_list_html}
        </ul>

        <div style="background-color: #f5f5f5; padding: 15px; border-radius: 4px; margin: 20px 0;">
            <p style="margin: 5px 0;"><strong>Kwota:</strong> {total_pln:.2f} PLN</p>
            <p style="margin: 5px 0;">
            <strong>Data:</strong> {order.created_at.strftime("%d.%m.%Y %H:%M")}</p>
        </div>

        <h3 style="color: #333; margin-top: 30px;">Ustaw hasło i zacznij pracę</h3>
        <p>Aby uzyskać dostęp do swoich pakietów, musisz ustawić hasło:</p>
        <p style="margin: 20px 0;">
            <a href="{reset_url}"
               style="background-color: #4CAF50; color: white; padding: 14px 28px;
                      text-decoration: none; border-radius: 4px; display: inline-block;
                      font-weight: bold;">
                Ustaw hasło i zaloguj się
            </a>
        </p>
        <p><strong>⚠️ Link wygasa za 1 godzinę.</strong></p>

        <p style="margin-top: 30px;">Po ustawieniu hasła przejdź do panelu:</p>
        <p><a href="{dashboard_url}" style="color: #4CAF50;">{dashboard_url}</a></p>

        <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
        <p style="font-size: 12px; color: #999;">
            © 2026 Efektywniejsi. Wszystkie prawa zastrzeżone.
        </p>
    </body>
    </html>
    """

    text_body = f"""
Witaj w Efektywniejsi! 🎉

Cześć {name},

Dziękujemy za zakup! Twoje zamówienie {order.order_number} zostało zrealizowane.

Zakupione pakiety:
{package_list_text}

Kwota: {total_pln:.2f} PLN
Data: {order.created_at.strftime("%d.%m.%Y %H:%M")}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

USTAW HASŁO I ZACZNIJ PRACĘ

Aby uzyskać dostęp do swoich pakietów, musisz ustawić hasło:
{reset_url}

⚠️ Link wygasa za 1 godzinę.

Po ustawieniu hasła przejdź do panelu:
{dashboard_url}

---
© 2026 Efektywniejsi. Wszystkie prawa zastrzeżone.
    """

    return EmailMessage(
        to=email,
        subject=f"Witaj w Efektywniejsi - Zamówienie {order.order_number}",
        body_html=html_body,
        body_text=text_body,
    )


def _build_purchase_confirmation_email(
    name: str,
    email: str,
    order: Order,
    enrollments: list[PackageEnrollment],
) -> EmailMessage:
    """Build purchase confirmation email for existing users."""
    dashboard_url = f"{settings.FRONTEND_URL}/dashboard/packages"

    # Build package list
    package_list_html = "".join(
        [
            f'<li style="margin: 10px 0;">{enrollment.package.title}</li>'
            for enrollment in enrollments
        ]
    )
    package_list_text = "\n".join([f"  • {enrollment.package.title}" for enrollment in enrollments])

    # Format price (from grosz to PLN)
    total_pln = order.total / 100

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2 style="color: #4CAF50;">Dziękujemy za zakup! 🎉</h2>
        <p>Cześć {name},</p>
        <p>Twoje zamówienie <strong>{order.order_number}</strong> zostało zrealizowane.</p>

        <h3 style="color: #333; margin-top: 25px;">Zakupione pakiety:</h3>
        <ul style="line-height: 2;">
            {package_list_html}
        </ul>

        <div style="background-color: #f5f5f5; padding: 15px; border-radius: 4px; margin: 20px 0;">
            <p style="margin: 5px 0;"><strong>Kwota:</strong> {total_pln:.2f} PLN</p>
            <p style="margin: 5px 0;">
            <strong>Data:</strong> {order.created_at.strftime("%d.%m.%Y %H:%M")}</p>
        </div>

        <p style="margin-top: 30px;">Wszystkie pakiety są już dostępne w Twoim panelu:</p>
        <p style="margin: 20px 0;">
            <a href="{dashboard_url}"
               style="background-color: #4CAF50; color: white; padding: 14px 28px;
                      text-decoration: none; border-radius: 4px; display: inline-block;
                      font-weight: bold;">
                Przejdź do panelu
            </a>
        </p>

        <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
        <p style="font-size: 12px; color: #999;">
            © 2026 Efektywniejsi. Wszystkie prawa zastrzeżone.
        </p>
    </body>
    </html>
    """

    text_body = f"""
Dziękujemy za zakup! 🎉

Cześć {name},

Twoje zamówienie {order.order_number} zostało zrealizowane.

Zakupione pakiety:
{package_list_text}

Kwota: {total_pln:.2f} PLN
Data: {order.created_at.strftime("%d.%m.%Y %H:%M")}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Wszystkie pakiety są już dostępne w Twoim panelu:
{dashboard_url}

---
© 2026 Efektywniejsi. Wszystkie prawa zastrzeżone.
    """

    return EmailMessage(
        to=email,
        subject=f"Zamówienie {order.order_number} zrealizowane",
        body_html=html_body,
        body_text=text_body,
    )
