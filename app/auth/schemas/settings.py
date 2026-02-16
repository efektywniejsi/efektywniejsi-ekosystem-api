from pydantic import BaseModel, Field


class ProfileUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    buyer_tax_no: str | None = Field(default=None, max_length=20)
    buyer_company_name: str | None = Field(default=None, max_length=200)
    buyer_street: str | None = Field(default=None, max_length=200)
    buyer_post_code: str | None = Field(default=None, max_length=20)
    buyer_city: str | None = Field(default=None, max_length=100)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)
    confirm_password: str


class TotpSetupResponse(BaseModel):
    secret: str
    qr_code_uri: str


class TotpVerifyRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)


class TotpStatusResponse(BaseModel):
    totp_enabled: bool


class NotificationPreferences(BaseModel):
    course_updates: bool = True
    admin_announcements: bool = False
    direct_messages: bool = True


class PaymentMethodResponse(BaseModel):
    id: str
    brand: str
    last4: str
    exp_month: int
    exp_year: int
    is_default: bool


class SetupIntentResponse(BaseModel):
    client_secret: str
