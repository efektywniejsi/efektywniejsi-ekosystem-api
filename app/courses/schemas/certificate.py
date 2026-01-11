from datetime import datetime

from pydantic import BaseModel


class CertificateResponse(BaseModel):
    id: str
    user_id: str
    course_id: str
    certificate_code: str
    issued_at: datetime
    file_path: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class CertificateWithCourseResponse(CertificateResponse):
    course_title: str
    course_slug: str
    user_name: str


class CertificateVerifyResponse(BaseModel):
    valid: bool
    certificate_code: str
    user_name: str
    course_title: str
    issued_at: datetime
    message: str
