from cryptography.fernet import Fernet

from app.core.config import settings


def _get_fernet() -> Fernet:
    return Fernet(settings.TOTP_ENCRYPTION_KEY.encode())


def encrypt_totp_secret(secret: str) -> str:
    return _get_fernet().encrypt(secret.encode()).decode()


def decrypt_totp_secret(encrypted: str) -> str:
    return _get_fernet().decrypt(encrypted.encode()).decode()
