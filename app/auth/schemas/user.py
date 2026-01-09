from pydantic import BaseModel


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str

    class Config:
        from_attributes = True
