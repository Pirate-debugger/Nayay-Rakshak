from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegister(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(
        ..., min_length=8, description="Minimum 8 characters with upper, lower, digit, special"
    )
    full_name: str = Field(..., min_length=2, max_length=150)


class UserLogin(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenRefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(..., description="Active cryptographic refresh token")


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: Optional[str] = None
    email: EmailStr
    full_name: str
    role: str
    is_demo: bool = False
    created_at: datetime


class TokenResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int = 900  # 15 minutes in seconds
    user: UserResponse


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: str
    family_id: str
    expires_at: datetime
    is_revoked: bool
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
