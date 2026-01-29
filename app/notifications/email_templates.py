from app.auth.services.email_service import (
    _BG_DARK,
    _BORDER,
    _CYAN,
    _TEXT_LIGHT,
    _TEXT_MUTED,
    _VIOLET,
    EmailMessage,
    _wrap_html,
)
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

    inner = f"""\
<h2 style="margin: 0 0 24px 0; font-size: 22px; font-weight: 700; color: {_TEXT_LIGHT};">
  {heading}
</h2>
<p style="margin: 0 0 16px 0; font-size: 15px; color: {_TEXT_MUTED}; line-height: 1.6;">
  Cześć {user_name},
</p>
<p style="margin: 0 0 20px 0; font-size: 15px; color: {_TEXT_MUTED}; line-height: 1.6;">
  {update_label} został dodany do kursu <strong style="color: {_TEXT_LIGHT};">{course_title}</strong>:
</p>
<div style="background-color: {_BG_DARK}; border: 1px solid {_BORDER}; border-radius: 8px; padding: 16px 20px; margin: 0 0 24px 0;">
  <p style="margin: 0; font-size: 16px; font-weight: 600; color: {_TEXT_LIGHT};">
    {item_title}
  </p>
</div>
<table cellpadding="0" cellspacing="0" style="margin: 0 0 8px 0;">
  <tr>
    <td style="border-radius: 8px; background: linear-gradient(135deg, {_VIOLET}, {_CYAN});">
      <a href="{course_url}"
         style="display: inline-block; padding: 12px 28px; font-size: 14px; font-weight: 600;
                color: #ffffff; text-decoration: none; border-radius: 8px;">
        Przejdź do kursu
      </a>
    </td>
  </tr>
</table>"""

    text_body = f"""\
{heading}

Cześć {user_name},

{update_label} został dodany do kursu {course_title}:

{item_title}

Przejdź do kursu: {course_url}

---
© 2026 Efektywniejsi. Wszystkie prawa zastrzeżone."""

    return EmailMessage(
        to=user_email,
        subject=heading,
        body_html=_wrap_html(inner),
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
    # Re-style the admin-provided HTML paragraphs for dark theme
    styled_body = body_html.replace(
        "<p>",
        f'<p style="margin: 0 0 12px 0; font-size: 15px; color: {_TEXT_MUTED}; line-height: 1.6;">',
    )

    inner = f"""\
<h2 style="margin: 0 0 24px 0; font-size: 22px; font-weight: 700; color: {_TEXT_LIGHT};">
  {subject}
</h2>
<p style="margin: 0 0 16px 0; font-size: 15px; color: {_TEXT_MUTED}; line-height: 1.6;">
  Cześć {user_name},
</p>
{styled_body}"""

    text_body = f"""\
{subject}

Cześć {user_name},

{body_text}

---
© 2026 Efektywniejsi. Wszystkie prawa zastrzeżone."""

    return EmailMessage(
        to=user_email,
        subject=subject,
        body_html=_wrap_html(inner),
        body_text=text_body,
    )
