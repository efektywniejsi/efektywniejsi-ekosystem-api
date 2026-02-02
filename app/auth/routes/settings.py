import uuid
from datetime import datetime

import pyotp
import stripe
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.models.user import User
from app.auth.schemas.settings import (
    ChangePasswordRequest,
    NotificationPreferences,
    PaymentMethodResponse,
    ProfileUpdateRequest,
    SetupIntentResponse,
    TotpSetupResponse,
    TotpStatusResponse,
    TotpVerifyRequest,
)
from app.core import security
from app.core.config import settings
from app.core.encryption import decrypt_totp_secret, encrypt_totp_secret
from app.core.storage import get_storage
from app.db.session import get_db

router = APIRouter()

ALLOWED_AVATAR_TYPES = {"image/jpeg", "image/png"}
MAX_AVATAR_SIZE = 2 * 1024 * 1024


@router.put("/profile")
async def update_profile(
    data: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    current_user.name = data.name
    db.commit()
    return {"message": "Profil zaktualizowany"}


@router.post("/profile/avatar")
async def upload_avatar(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    if file.content_type not in ALLOWED_AVATAR_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dozwolone są tylko pliki JPG i PNG",
        )

    contents = await file.read()
    if len(contents) > MAX_AVATAR_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rozmiar pliku przekracza limit 2MB",
        )

    storage = get_storage()

    ext = "jpg" if file.content_type == "image/jpeg" else "png"
    filename = f"{uuid.uuid4()}.{ext}"

    stored_path = storage.upload(contents, "avatars", filename)

    if current_user.avatar_url:
        try:
            storage.delete(current_user.avatar_url)
        except Exception:
            pass

    avatar_url = storage.download_url(stored_path)
    current_user.avatar_url = avatar_url
    db.commit()

    return {"avatar_url": avatar_url}


@router.delete("/profile/avatar")
async def delete_avatar(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    if current_user.avatar_url:
        storage = get_storage()
        try:
            storage.delete(current_user.avatar_url)
        except Exception:
            pass
        current_user.avatar_url = None
        db.commit()
    return {"message": "Zdjęcie usunięte"}


@router.post("/password")
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    if data.new_password != data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hasła nie są identyczne",
        )

    if not security.verify_password(data.current_password, str(current_user.hashed_password)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Obecne hasło jest nieprawidłowe",
        )

    current_user.hashed_password = security.get_password_hash(data.new_password)
    current_user.password_changed_at = datetime.utcnow()
    db.commit()

    return {"message": "Hasło zostało zmienione"}


@router.post("/2fa/setup", response_model=TotpSetupResponse)
async def setup_2fa(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TotpSetupResponse:
    secret = pyotp.random_base32()
    current_user.totp_secret = encrypt_totp_secret(secret)
    db.commit()

    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=current_user.email, issuer_name="Efektywniejsi")

    return TotpSetupResponse(secret=secret, qr_code_uri=uri)


@router.post("/2fa/verify")
async def verify_2fa(
    data: TotpVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Konfiguracja 2FA nie została rozpoczęta",
        )

    totp = pyotp.TOTP(decrypt_totp_secret(current_user.totp_secret))
    if not totp.verify(data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nieprawidłowy kod weryfikacyjny",
        )

    current_user.totp_enabled = True
    db.commit()

    return {"message": "2FA włączone"}


@router.post("/2fa/disable")
async def disable_2fa(
    data: TotpVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    if not current_user.totp_enabled or not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA nie jest włączone",
        )

    totp = pyotp.TOTP(decrypt_totp_secret(current_user.totp_secret))
    if not totp.verify(data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nieprawidłowy kod weryfikacyjny",
        )

    current_user.totp_enabled = False
    current_user.totp_secret = None
    db.commit()

    return {"message": "2FA wyłączone"}


@router.get("/2fa/status", response_model=TotpStatusResponse)
async def get_2fa_status(
    current_user: User = Depends(get_current_user),
) -> TotpStatusResponse:
    return TotpStatusResponse(totp_enabled=current_user.totp_enabled)


def _get_or_create_stripe_customer(user: User, db: Session) -> str:
    if user.stripe_customer_id:
        return str(user.stripe_customer_id)

    customer = stripe.Customer.create(
        email=user.email,
        name=user.name,
        metadata={"user_id": str(user.id)},
    )
    user.stripe_customer_id = customer.id
    db.commit()
    return str(customer.id)


@router.get("/payments/methods", response_model=list[PaymentMethodResponse])
async def get_payment_methods(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PaymentMethodResponse]:
    if not current_user.stripe_customer_id:
        return []

    stripe.api_key = settings.STRIPE_SECRET_KEY
    methods = stripe.PaymentMethod.list(
        customer=current_user.stripe_customer_id,
        type="card",
    )

    customer = stripe.Customer.retrieve(current_user.stripe_customer_id)
    default_pm_id = None
    if customer.invoice_settings and customer.invoice_settings.default_payment_method:
        default_pm_id = customer.invoice_settings.default_payment_method

    result = []
    for pm in methods.data:
        card = pm.card
        if card is None:
            continue
        result.append(
            PaymentMethodResponse(
                id=pm.id,
                brand=card.brand,
                last4=card.last4,
                exp_month=card.exp_month,
                exp_year=card.exp_year,
                is_default=pm.id == default_pm_id,
            )
        )
    return result


@router.post("/payments/setup-intent", response_model=SetupIntentResponse)
async def create_setup_intent(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SetupIntentResponse:
    stripe.api_key = settings.STRIPE_SECRET_KEY
    customer_id = _get_or_create_stripe_customer(current_user, db)

    intent = stripe.SetupIntent.create(
        customer=customer_id,
        payment_method_types=["card"],
    )

    return SetupIntentResponse(client_secret=intent.client_secret)


@router.delete("/payments/methods/{method_id}")
async def delete_payment_method(
    method_id: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        pm = stripe.PaymentMethod.retrieve(method_id)
        if pm.customer != current_user.stripe_customer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Metoda płatności nie należy do tego użytkownika",
            )
        stripe.PaymentMethod.detach(method_id)
    except stripe.InvalidRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metoda płatności nie znaleziona",
        ) from exc

    return {"message": "Metoda płatności usunięta"}


@router.get("/notifications", response_model=NotificationPreferences)
async def get_notification_preferences(
    current_user: User = Depends(get_current_user),
) -> NotificationPreferences:
    prefs = current_user.notification_preferences
    if prefs:
        return NotificationPreferences(**prefs)
    return NotificationPreferences()


@router.put("/notifications", response_model=NotificationPreferences)
async def update_notification_preferences(
    data: NotificationPreferences,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationPreferences:
    current_user.notification_preferences = data.model_dump()
    db.commit()
    return data
