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


def build_admin_reply_email(
    user_name: str,
    user_email: str,
    ticket_subject: str,
    reply_preview: str,
) -> EmailMessage:
    ticket_url = f"{settings.FRONTEND_URL}/wsparcie"

    inner = f"""\
<h2 style="margin: 0 0 24px 0; font-size: 22px; font-weight: 700; color: {_TEXT_LIGHT};">
  Nowa odpowiedź na Twoje zgłoszenie
</h2>
<p style="margin: 0 0 16px 0; font-size: 15px; color: {_TEXT_MUTED}; line-height: 1.6;">
  Cześć {user_name},
</p>
<p style="margin: 0 0 20px 0; font-size: 15px; color: {_TEXT_MUTED}; line-height: 1.6;">
  Otrzymaliśmy odpowiedź na Twoje zgłoszenie
  <strong style="color: {_TEXT_LIGHT};">„{ticket_subject}"</strong>.
</p>
<div style="background-color: {_BG_DARK}; border: 1px solid {_BORDER};
     border-radius: 8px; padding: 16px 20px; margin: 0 0 24px 0;">
  <p style="margin: 0; font-size: 14px; color: {_TEXT_MUTED};
     line-height: 1.6; font-style: italic;">
    „{reply_preview}"
  </p>
</div>
<table cellpadding="0" cellspacing="0" style="margin: 0 0 24px 0;">
  <tr>
    <td style="border-radius: 8px; background: linear-gradient(135deg, {_VIOLET}, {_CYAN});">
      <a href="{ticket_url}"
         style="display: inline-block; padding: 12px 28px; font-size: 14px; font-weight: 600;
                color: #ffffff; text-decoration: none; border-radius: 8px;">
        Zobacz zgłoszenie
      </a>
    </td>
  </tr>
</table>
<p style="margin: 0; font-size: 13px; color: {_TEXT_MUTED}; line-height: 1.5;">
  Możesz odpowiedzieć bezpośrednio w panelu.
</p>"""

    text_body = f"""\
Nowa odpowiedź na Twoje zgłoszenie - Efektywniejsi

Cześć {user_name},

Otrzymaliśmy odpowiedź na Twoje zgłoszenie „{ticket_subject}".

„{reply_preview}"

Zobacz zgłoszenie: {ticket_url}

---
© 2026 Efektywniejsi. Wszystkie prawa zastrzeżone."""

    return EmailMessage(
        to=user_email,
        subject=f"Odpowiedź na zgłoszenie: {ticket_subject}",
        body_html=_wrap_html(inner),
        body_text=text_body,
    )
