from app.auth.services.email_service import EmailMessage
from app.core.config import settings


def build_course_update_email(
    user_name: str,
    user_email: str,
    course_title: str,
    course_slug: str,
    update_type: str,
    item_title: str,
) -> EmailMessage:
    """Build an email notifying a user about a new lesson or module in a course."""
    course_url = f"{settings.FRONTEND_URL}/kursy/{course_slug}"

    if update_type == "new_lesson":
        update_label = "Nowa lekcja"
        heading = f"Nowa lekcja w kursie: {course_title}"
    else:
        update_label = "Nowy moduł"
        heading = f"Nowy moduł w kursie: {course_title}"

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2 style="color: #4CAF50;">{heading}</h2>
        <p>Cześć {user_name},</p>
        <p>{update_label} został dodany do kursu <strong>{course_title}</strong>:</p>
        <div style="background-color: #f5f5f5; padding: 15px; border-radius: 4px; margin: 20px 0;">
            <p style="margin: 0; font-size: 16px;"><strong>{item_title}</strong></p>
        </div>
        <p style="margin: 20px 0;">
            <a href="{course_url}"
               style="background-color: #4CAF50; color: white; padding: 12px 24px;
                      text-decoration: none; border-radius: 4px; display: inline-block;">
                Przejdź do kursu
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
{heading}

Cześć {user_name},

{update_label} został dodany do kursu {course_title}:

{item_title}

Przejdź do kursu: {course_url}

---
© 2026 Efektywniejsi. Wszystkie prawa zastrzeżone.
    """

    return EmailMessage(
        to=user_email,
        subject=heading,
        body_html=html_body,
        body_text=text_body,
    )


def build_announcement_email(
    user_name: str,
    user_email: str,
    subject: str,
    body_html: str,
    body_text: str,
) -> EmailMessage:
    """Build an announcement email from the admin."""
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2 style="color: #4CAF50;">{subject}</h2>
        <p>Cześć {user_name},</p>
        {body_html}
        <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
        <p style="font-size: 12px; color: #999;">
            © 2026 Efektywniejsi. Wszystkie prawa zastrzeżone.
        </p>
    </body>
    </html>
    """

    text_body = f"""
{subject}

Cześć {user_name},

{body_text}

---
© 2026 Efektywniejsi. Wszystkie prawa zastrzeżone.
    """

    return EmailMessage(
        to=user_email,
        subject=subject,
        body_html=html_body,
        body_text=text_body,
    )
