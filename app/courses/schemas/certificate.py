from pydantic import BaseModel

from app.core.datetime_utils import UTCDatetime


class CertificateResponse(BaseModel):
    id: str
    user_id: str
    course_id: str
    certificate_code: str
    issued_at: UTCDatetime
    file_path: str | None = None
    created_at: UTCDatetime

    class Config:
        from_attributes = True


class CertificateWithCourseResponse(CertificateResponse):
    course_title: str
    course_slug: str
    user_name: str


class CertificateVerifyResponse(BaseModel):
    valid: bool
    certificate_code: str
    user_name: str | None = None
    course_title: str | None = None
    issued_at: UTCDatetime | None = None
    message: str
