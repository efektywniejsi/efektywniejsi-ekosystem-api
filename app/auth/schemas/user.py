from pydantic import BaseModel


class UserResponse(BaseModel):
    """
    User response schema for API responses.
    Returns user data without sensitive information.
    """

    id: str
    email: str
    name: str
    role: str

    class Config:
        from_attributes = True
