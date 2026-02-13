import logging

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

logger = logging.getLogger(__name__)

_fernet_instance: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet_instance
    if _fernet_instance is not None:
        return _fernet_instance

    key = settings.TOTP_ENCRYPTION_KEY
    if not key:
        raise RuntimeError(
            "TOTP_ENCRYPTION_KEY nie jest skonfigurowany. "
            "Wygeneruj klucz: python -c "
            "'from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())'"
        )
    try:
        _fernet_instance = Fernet(key.encode())
    except (ValueError, InvalidToken) as e:
        raise RuntimeError(
            f"TOTP_ENCRYPTION_KEY jest nieprawidłowy (nie jest poprawnym kluczem Fernet): {e}"
        ) from e
    return _fernet_instance


def encrypt_totp_secret(secret: str) -> str:
    return _get_fernet().encrypt(secret.encode()).decode()


def decrypt_totp_secret(encrypted: str) -> str:
    return _get_fernet().decrypt(encrypted.encode()).decode()
