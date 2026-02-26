from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthenticatedUser(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: str
    location_ids: list[str]


class LoginResponse(BaseModel):
    user: AuthenticatedUser


class RefreshResponse(BaseModel):
    refreshed: bool
